"""
`ridego.model` — a camada MODEL do padrão MVC, num único arquivo.

Contém apenas dados e regras de negócio — nenhuma linha deste arquivo sabe
desenhar um pixel na tela (isso é responsabilidade de `views.py`) nem
decide para qual tela navegar (isso é responsabilidade de `controller.py`).
Essa separação é o coração do MVC: se um dia o app trocar de framework de
UI (Flet -> outro), este arquivo continua igual.

Está dividido em 4 blocos, na ordem em que um bloco depende do anterior:

1. Entidades de dados (`RideCategory`, `Destination`, `Ride`)
2. Motoristas (`Driver`, `DriverPool`)
3. Catálogo fixo (categorias e destinos rápidos)
4. Estado do app (`RideState`) — usa tudo dos blocos anteriores
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import uuid4

import flet as ft

# ---------------------------------------------------------------------------
# 1) Entidades de dados
# ---------------------------------------------------------------------------
# Usamos `@dataclass` porque ele já nos dá, de graça, o construtor
# (`__init__`), a representação em texto (`__repr__`) e a comparação por
# valor (`__eq__`) — Programação Orientada a Objetos "por baixo dos panos",
# sem o código repetitivo (boilerplate) que teríamos escrevendo na mão.


@dataclass
class RideCategory:
    """
    Uma categoria de corrida disponível (Econômico, Comfort, XL...).

    Guarda só os dados/parâmetros de precificação da categoria. O CÁLCULO
    do preço em si não é responsabilidade desta classe — isso fica a
    cargo do `PricingService` (ver `services.py`), para manter cada classe
    com uma única responsabilidade.
    """
    id: str
    name: str
    emoji: str
    base_fare: float       # tarifa fixa de bandeirada, em R$
    price_per_km: float    # custo por km rodado, em R$
    price_per_min: float   # custo por minuto de viagem, em R$
    avg_speed_kmh: float    # velocidade média assumida, usada para estimar duração
    seats: int              # lugares disponíveis no veículo


@dataclass
class Destination:
    """
    Um destino de corrida: um dos "chips" rápidos pré-cadastrados, ou um
    endereço digitado livremente pelo usuário e resolvido por um
    `AddressResolutionService` (ver `services.py`).

    Existem duas formas de representar ONDE fica o destino, e a classe
    aceita as duas:

    1. **Relativa** (`distance_km` + `bearing_deg`): um deslocamento
       (distância + direção) a partir da origem. É o que os destinos
       rápidos usam (cadastrados abaixo, em `QUICK_DESTINATIONS`) —
       assim eles funcionam em qualquer lugar do mundo, sem depender de
       coordenadas fixas.
    2. **Absoluta** (`lat` + `lon`): a coordenada real do endereço,
       devolvida pelo serviço de geocodificação (Nominatim/OpenStreetMap)
       quando o usuário digita um endereço de verdade. Quando presente,
       tem PRIORIDADE sobre a relativa — é o que garante que o app aponte
       para a rua realmente pesquisada, e não para um lugar simulado.
    """
    label: str
    emoji: str
    distance_km: float           # distância em linha reta a partir da origem
    bearing_deg: float = 0.0     # direção a partir da origem, em graus (0 = norte)
    lat: float | None = None     # coordenada real (quando vinda de geocodificação)
    lon: float | None = None     # coordenada real (quando vinda de geocodificação)
    is_simulated: bool = False   # True quando NÃO foi possível geocodificar de verdade

    @property
    def has_real_coordinates(self) -> bool:
        """`True` quando este destino tem uma coordenada real (não relativa/simulada)."""
        return self.lat is not None and self.lon is not None


@dataclass
class Ride:
    """
    Uma corrida já concluída e avaliada — o que fica salvo no histórico do
    usuário (persistido localmente via `SharedPreferences`).
    """
    id: str
    origin_label: str
    destination_label: str
    category_name: str
    category_emoji: str
    distance_km: float
    duration_min: float
    price: float
    driver_name: str
    car_model: str
    plate: str
    rating: int
    comment: str
    created_at: str

    def to_dict(self) -> dict:
        """Serializa a corrida para um dicionário simples (pronto para JSON)."""
        return self.__dict__.copy()

    @staticmethod
    def from_dict(data: dict) -> "Ride":
        """Reconstrói uma `Ride` a partir de um dicionário (o inverso de `to_dict`)."""
        return Ride(**data)


# ---------------------------------------------------------------------------
# 2) Motoristas
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Driver:
    """
    Um motorista fictício. `frozen=True` torna as instâncias imutáveis
    (não dá para reatribuir `driver.name = ...` depois de criado) — um
    pequeno exemplo de encapsulamento: uma vez sorteado, os dados do
    motorista da corrida atual não podem ser alterados por acidente.
    """
    name: str
    car_model: str
    plate: str

    @property
    def initial(self) -> str:
        """Inicial do nome — usada como avatar quando não há foto do motorista."""
        return self.name[0].upper() if self.name else "?"

    def __str__(self) -> str:  # pragma: no cover - só para depuração/logs
        return f"{self.name} ({self.car_model}, placa {self.plate})"


class DriverPool:
    """
    Repositório dos motoristas fictícios disponíveis no exercício.

    Os motoristas em si (`_drivers`) ficam num atributo "privado" (prefixo
    `_`) — o resto do app nunca deve acessar essa lista diretamente, e sim
    passar sempre pelo método público `pick_random()`. Isso é encapsulamento:
    a classe controla como seus dados internos podem ser usados.
    """

    def __init__(self) -> None:
        self._drivers: list[Driver] = [
            Driver("Sabrina Carpenter", "Chevrolet Onix Prata", "BRA2E19"),
            Driver("Shakira", "Fiat Argo Branco", "FGX4A21"),
            Driver("Ariana Grande", "Hyundai HB20 Preto", "KLT9B33"),
            Driver("Dua Lipa", "Renault Kwid Vermelho", "PQR1C77"),
            Driver("Taylor Swift", "Volkswagen Polo Cinza", "ABC5D88"),
            Driver("Pitty", "Toyota Yaris Azul", "XYZ7F42"),
        ]

    def pick_random(self) -> Driver:
        """Sorteia um motorista disponível para a corrida atual."""
        return random.choice(self._drivers)

    def all(self) -> tuple[Driver, ...]:
        """Retorna uma cópia somente-leitura (tupla) dos motoristas cadastrados."""
        return tuple(self._drivers)


# ---------------------------------------------------------------------------
# 3) Catálogo de dados fixos do domínio
# ---------------------------------------------------------------------------
# Categorias de corrida disponíveis (preços fictícios, só para o exercício).
CATEGORIES: list[RideCategory] = [
    RideCategory(
        id="economico", name="Econômico", emoji="🚗",
        base_fare=4.00, price_per_km=1.80, price_per_min=0.25,
        avg_speed_kmh=28, seats=4,
    ),
    RideCategory(
        id="comfort", name="Comfort", emoji="🚙",
        base_fare=6.00, price_per_km=2.40, price_per_min=0.35,
        avg_speed_kmh=30, seats=4,
    ),
    RideCategory(
        id="xl", name="XL", emoji="🚐",
        base_fare=8.00, price_per_km=3.00, price_per_min=0.45,
        avg_speed_kmh=26, seats=6,
    ),
]

# Destinos fictícios, sempre calculados como um deslocamento (distância +
# direção) a partir da localização atual do usuário — assim o exercício
# funciona em qualquer lugar do mundo, sem precisar de um serviço real de
# geocodificação/busca de endereços.
QUICK_DESTINATIONS: list[Destination] = [
    Destination("Aeroporto", "✈️", distance_km=12, bearing_deg=45),
    Destination("Shopping Central", "🛍️", distance_km=5, bearing_deg=120),
    Destination("Centro da Cidade", "🏙️", distance_km=3, bearing_deg=200),
    Destination("Estádio Municipal", "🏟️", distance_km=8, bearing_deg=300),
    Destination("Universidade", "🎓", distance_km=6, bearing_deg=60),
]


def find_category_by_id(category_id: str) -> RideCategory:
    """Busca uma `RideCategory` cadastrada pelo seu `id` (ex.: 'comfort')."""
    return next(c for c in CATEGORIES if c.id == category_id)


# ---------------------------------------------------------------------------
# 4) Estado do app
# ---------------------------------------------------------------------------
HISTORY_KEY = "ridego_history"
DEFAULT_ORIGIN = (-23.5505, -46.6333)  # usado só se o GPS não estiver disponível


class RideState:
    """
    Estado do app, com os atributos "sensíveis" guardados como privados
    (prefixo `_`) e expostos ao resto do app somente por meio de
    `@property` — um exemplo direto de ENCAPSULAMENTO: quem usa
    `ride_state.destination` está sempre lendo o valor atual, sem risco de
    sobrescrevê-lo por engano com um tipo errado, e sem precisar conhecer
    os detalhes internos de como o dado é guardado.
    """

    def __init__(self) -> None:
        self._drivers = DriverPool()

        # Histórico de corridas concluídas (persistido via SharedPreferences)
        self._history: list[Ride] = []
        self._prefs: Optional[ft.SharedPreferences] = None

        # Seleção da corrida em andamento (fluxo Home -> Categorias -> Corrida -> Avaliação)
        self._origin_label: str = "Minha localização"
        self._origin_coords: tuple[float, float] = DEFAULT_ORIGIN
        self._destination: Optional[Destination] = None
        self._destination_coords: Optional[tuple[float, float]] = None
        self._selected_category: Optional[RideCategory] = None
        self._current_driver: Optional[Driver] = None
        self._current_price: float = 0.0
        self._current_duration: float = 0.0

    # ------------------------------------------------------------------
    # Propriedades somente-leitura (o resto do app só pode ler estes
    # valores; para alterá-los é preciso passar pelos métodos abaixo, que
    # sabem manter tudo consistente).
    # ------------------------------------------------------------------
    @property
    def origin_label(self) -> str:
        return self._origin_label

    @property
    def origin_coords(self) -> tuple[float, float]:
        return self._origin_coords

    @property
    def destination(self) -> Optional[Destination]:
        return self._destination

    @property
    def destination_coords(self) -> Optional[tuple[float, float]]:
        return self._destination_coords

    @property
    def selected_category(self) -> Optional[RideCategory]:
        return self._selected_category

    @property
    def current_driver(self) -> Optional[Driver]:
        return self._current_driver

    @property
    def current_price(self) -> float:
        return self._current_price

    @property
    def current_duration(self) -> float:
        return self._current_duration

    @property
    def history(self) -> tuple[Ride, ...]:
        """Cópia somente-leitura do histórico (impede `state.history.append(...)`)."""
        return tuple(self._history)

    # ------------------------------------------------------------------
    # Persistência (SharedPreferences do dispositivo)
    # ------------------------------------------------------------------
    def bind(self, prefs: ft.SharedPreferences) -> None:
        """Associa o serviço de armazenamento local — chamado uma vez, no início do app."""
        self._prefs = prefs

    async def load_history(self) -> None:
        """Carrega o histórico salvo do dispositivo (se houver)."""
        raw = await self._prefs.get(HISTORY_KEY)
        self._history = [Ride.from_dict(d) for d in json.loads(raw)] if raw else []

    async def _persist_history(self) -> None:
        """Salva o histórico atual no dispositivo."""
        payload = json.dumps([ride.to_dict() for ride in self._history])
        await self._prefs.set(HISTORY_KEY, payload)

    async def clear_history(self) -> None:
        """Apaga todo o histórico de corridas (em memória e no dispositivo)."""
        self._history = []
        await self._persist_history()

    # ------------------------------------------------------------------
    # Mutações de estado (única porta de entrada para alterar os dados)
    # ------------------------------------------------------------------
    def set_origin(self, coords: tuple[float, float], label: str) -> None:
        self._origin_coords = coords
        self._origin_label = label

    def set_destination(self, destination: Destination, coords: tuple[float, float]) -> None:
        self._destination = destination
        self._destination_coords = coords

    def select_category(self, category: RideCategory, price: float, duration: float) -> None:
        """Confirma a categoria escolhida e sorteia o motorista da corrida atual."""
        self._selected_category = category
        self._current_price = price
        self._current_duration = duration
        self._current_driver = self._drivers.pick_random()

    async def finish_ride(self, rating: int, comment: str) -> Ride:
        """
        Fecha a corrida atual: monta o registro de `Ride`, adiciona ao
        histórico, persiste no dispositivo e limpa a seleção em andamento
        (para o app voltar pronto para uma nova corrida).
        """
        assert self._destination is not None
        assert self._selected_category is not None
        assert self._current_driver is not None

        driver = self._current_driver
        ride = Ride(
            id=uuid4().hex[:8],
            origin_label=self._origin_label,
            destination_label=self._destination.label,
            category_name=self._selected_category.name,
            category_emoji=self._selected_category.emoji,
            distance_km=self._destination.distance_km,
            duration_min=self._current_duration,
            price=self._current_price,
            driver_name=driver.name,
            car_model=driver.car_model,
            plate=driver.plate,
            rating=rating,
            comment=comment,
            created_at=datetime.now().strftime("%d/%m/%Y %H:%M"),
        )
        self._history.insert(0, ride)
        await self._persist_history()
        self._reset_current_ride()
        return ride

    def _reset_current_ride(self) -> None:
        """Limpa a seleção da corrida atual, mantendo o histórico intacto."""
        self._destination = None
        self._destination_coords = None
        self._selected_category = None
        self._current_driver = None
        self._current_price = 0.0
        self._current_duration = 0.0
