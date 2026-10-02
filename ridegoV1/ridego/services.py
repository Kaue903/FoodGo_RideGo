"""
`ridego.services` — serviços auxiliares, num único arquivo.

Classes com uma responsabilidade única (cálculo de geolocalização,
precificação, geocodificação de endereço). Elas não guardam estado do app
(não sabem qual é a corrida atual, por exemplo) — só recebem dados de
entrada e devolvem um resultado. Isso os torna fáceis de testar
isoladamente e de reaproveitar tanto no `model` quanto no `controller`.
"""
from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod

import httpx

from ridego.model import Destination, RideCategory

# ---------------------------------------------------------------------------
# Geografia e precificação (sem depender de nenhuma API paga de mapas/rotas)
# ---------------------------------------------------------------------------


class GeoService:
    """
    Responsável apenas pela matemática de geolocalização: dado um ponto de
    partida, uma distância e uma direção, calcula o ponto de chegada.

    Todos os métodos são `staticmethod` porque a classe não precisa guardar
    nenhum estado próprio — ela existe só para agrupar essas operações sob
    um nome coeso (`GeoService.offset_point(...)`), em vez de deixar uma
    função solta no módulo.
    """

    EARTH_RADIUS_KM = 6371.0  # raio médio da Terra, em km

    @staticmethod
    def offset_point(
        lat: float, lon: float, distance_km: float, bearing_deg: float
    ) -> tuple[float, float]:
        """
        Calcula um ponto a `distance_km` de distância e `bearing_deg` graus
        de direção a partir de (lat, lon).

        É uma aproximação simples (Terra esférica), suficiente para um
        exercício de UI — não é uma ferramenta de geocodificação real.
        """
        bearing = math.radians(bearing_deg)
        lat1 = math.radians(lat)
        lon1 = math.radians(lon)
        radius = GeoService.EARTH_RADIUS_KM

        lat2 = math.asin(
            math.sin(lat1) * math.cos(distance_km / radius)
            + math.cos(lat1) * math.sin(distance_km / radius) * math.cos(bearing)
        )
        lon2 = lon1 + math.atan2(
            math.sin(bearing) * math.sin(distance_km / radius) * math.cos(lat1),
            math.cos(distance_km / radius) - math.sin(lat1) * math.sin(lat2),
        )
        return math.degrees(lat2), math.degrees(lon2)

    @staticmethod
    def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Distância em linha reta (grande círculo) entre dois pontos, em km.
        Usada para calcular a distância real até um endereço geocodificado
        (onde já temos as duas coordenadas, em vez de distância + direção).
        """
        radius = GeoService.EARTH_RADIUS_KM
        lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
        lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)

        delta_lat = lat2_r - lat1_r
        delta_lon = lon2_r - lon1_r
        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return radius * c


class PricingService:
    """
    Responsável apenas por transformar (categoria + distância) em
    (preço estimado, duração estimada) — a "calculadora de tarifas" do app.
    """

    @staticmethod
    def estimate(category: RideCategory, distance_km: float) -> tuple[float, float]:
        """Retorna `(preço estimado em R$, duração estimada em minutos)`."""
        duration_min = (distance_km / category.avg_speed_kmh) * 60
        price = (
            category.base_fare
            + category.price_per_km * distance_km
            + category.price_per_min * duration_min
        )
        return round(price, 2), round(duration_min, 1)


# ---------------------------------------------------------------------------
# Geocodificação: endereço digitado -> coordenadas REAIS (Nominatim/OSM)
# ---------------------------------------------------------------------------
# Usa o padrão de projeto STRATEGY (mais um exemplo de ABSTRAÇÃO +
# POLIMORFISMO no projeto): `GeocodingStrategy` é uma interface comum com
# duas implementações concretas:
#
# * `NominatimGeocodingStrategy` — a "de verdade", consulta a internet.
# * `SimulatedGeocodingStrategy` — o cálculo por hash, usado SÓ como último
#   recurso, se não houver internet.
#
# `AddressResolutionService` tenta sempre a primeira; só cai na segunda em
# caso de falha de REDE (sem internet, timeout, serviço fora do ar) — nunca
# quando o endereço simplesmente não existe. Nesse caso, uma
# `AddressNotFoundError` é levantada e a View deve avisar o usuário, em vez
# de "inventar" uma localização qualquer no mapa.


class AddressNotFoundError(Exception):
    """
    Levantada quando o endereço digitado é consultado com sucesso, mas o
    Nominatim não encontra nenhum resultado para ele — ou seja, o
    endereço provavelmente está incompleto ou não existe, e não um
    problema de rede.
    """


class GeocodingStrategy(ABC):
    """Interface comum a qualquer forma de resolver um endereço em coordenadas."""

    @abstractmethod
    async def geocode(self, address: str) -> Destination:
        """Deve devolver um `Destination` para o endereço, ou levantar uma exceção."""
        raise NotImplementedError


class NominatimGeocodingStrategy(GeocodingStrategy):
    """
    Geocodificação REAL usando o serviço público do Nominatim
    (https://nominatim.org/), gratuito e sem precisar de chave de API.

    Política de uso do Nominatim (importante se for reaproveitar este
    código em produção): no máximo ~1 requisição por segundo, é
    obrigatório informar um `User-Agent` identificando a aplicação, e o
    serviço não deve ser usado para busca "enquanto digita"
    (autocomplete). Aqui só disparamos uma consulta por clique/Enter
    explícito do usuário, o que já respeita essa regra.
    """

    SEARCH_URL = "https://nominatim.openstreetmap.org/search"
    USER_AGENT = "RideGo-Exercise/1.0 (uso educacional; sem fins comerciais)"
    REQUEST_TIMEOUT_SECONDS = 8.0

    async def geocode(self, address: str) -> Destination:
        params = {"q": address, "format": "jsonv2", "limit": 1, "addressdetails": 0}
        headers = {"User-Agent": self.USER_AGENT}

        async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.get(self.SEARCH_URL, params=params, headers=headers)
            response.raise_for_status()
            results = response.json()

        if not results:
            raise AddressNotFoundError(f'Nenhum resultado encontrado para "{address}".')

        result = results[0]
        return Destination(
            label=self._short_label(result.get("display_name", address)),
            emoji="📍",
            distance_km=0.0,  # recalculada pelo controller, já em relação à origem atual
            lat=float(result["lat"]),
            lon=float(result["lon"]),
            is_simulated=False,
        )

    @staticmethod
    def _short_label(display_name: str) -> str:
        """
        O Nominatim devolve um endereço bem completo e longo (ex.: "Av.
        Paulista, 1000, Bela Vista, São Paulo, Região Metropolitana de São
        Paulo, SP, 01310-100, Brasil"). Para caber bem na UI, mostramos só
        os 3 primeiros pedaços (geralmente: via, número/bairro, cidade).
        """
        parts = [p.strip() for p in display_name.split(",")]
        return ", ".join(parts[:3]) if len(parts) > 3 else display_name


class SimulatedGeocodingStrategy(GeocodingStrategy):
    """
    Fallback usado SOMENTE quando a geocodificação real falha por
    problema de rede/conectividade — nunca quando o endereço simplesmente
    não existe (nesse caso quem chama deve mostrar `AddressNotFoundError`
    ao usuário, e não fingir um resultado).

    Deriva uma distância e direção plausíveis a partir de um hash do
    próprio texto digitado — determinístico (mesmo endereço = mesmo
    resultado), e sempre marcado como `is_simulated=True`, para a tela
    poder avisar claramente que aquilo é uma aproximação, nunca disfarçado
    de resultado real.
    """

    MIN_DISTANCE_KM = 1.5
    MAX_DISTANCE_KM = 21.5

    async def geocode(self, address: str) -> Destination:
        normalized = address.strip()
        digest = hashlib.sha256(normalized.lower().encode("utf-8")).hexdigest()
        span_km = self.MAX_DISTANCE_KM - self.MIN_DISTANCE_KM
        distance_km = self.MIN_DISTANCE_KM + (int(digest[:8], 16) % 2000) / 2000 * span_km
        bearing_deg = int(digest[8:12], 16) % 360
        return Destination(
            label=normalized,
            emoji="📍",
            distance_km=round(distance_km, 1),
            bearing_deg=bearing_deg,
            is_simulated=True,
        )


class AddressResolutionService:
    """
    Fachada usada pelo `RideController`: tenta geocodificar de verdade e
    só recorre à simulação em caso de falha de conectividade.
    """

    def __init__(
        self,
        real_strategy: GeocodingStrategy | None = None,
        fallback_strategy: GeocodingStrategy | None = None,
    ) -> None:
        # Injeção de dependência com valores padrão — permite trocar a
        # estratégia (por exemplo, em testes automatizados) sem alterar
        # esta classe.
        self._real_strategy = real_strategy or NominatimGeocodingStrategy()
        self._fallback_strategy = fallback_strategy or SimulatedGeocodingStrategy()

    async def resolve(self, address: str) -> Destination:
        """
        Devolve um `Destination` para o endereço digitado.

        Deixa `AddressNotFoundError` propagar — quem chama deve avisar o
        usuário e pedir para refinar a busca. Só recorre ao fallback
        simulado para erros de rede/conectividade (`httpx.HTTPError`).
        """
        try:
            return await self._real_strategy.geocode(address)
        except AddressNotFoundError:
            raise
        except httpx.HTTPError:
            return await self._fallback_strategy.geocode(address)
