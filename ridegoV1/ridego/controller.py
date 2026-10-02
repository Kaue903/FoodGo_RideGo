"""
`ridego.controller` — a camada CONTROLLER do padrão MVC.

Recebe os eventos que a View dispara (usuário tocou em tal botão, digitou
tal endereço, etc.), aciona o Model e os Services para processar a regra
de negócio, e devolve para a View só o resultado já pronto para desenhar.
As Views não conhecem `RideState` nem os `services` diretamente — só
conhecem `RideController`. Essa indireção é o que permite trocar a forma
como os dados são calculados/guardados sem precisar tocar em nenhuma tela.
"""
from __future__ import annotations

import flet as ft
import flet_geolocator as ftg

from ridego.model import Destination, Ride, RideCategory, RideState, find_category_by_id
from ridego.services import AddressResolutionService, GeoService, PricingService


class RideController:
    """
    Orquestra o fluxo de uma corrida: origem -> destino -> categoria ->
    corrida em andamento -> avaliação -> histórico.

    Os atributos `_state`, `_pricing_service`, etc. são privados: o app
    inteiro interage com o controller só através dos métodos públicos
    definidos abaixo (encapsulamento). Isso mantém as regras de negócio
    centralizadas num único lugar, fáceis de revisar e de testar.
    """

    def __init__(self, page: ft.Page) -> None:
        self._page = page
        self._state = RideState()
        self._pricing_service = PricingService()
        self._geo_service = GeoService()
        self._address_service = AddressResolutionService()

    # ------------------------------------------------------------------
    # Ciclo de vida / persistência
    # ------------------------------------------------------------------
    async def initialize(self) -> None:
        """
        Prepara o controller para uso: registra o serviço de armazenamento
        local (`SharedPreferences`) e carrega o histórico de corridas já
        salvo no dispositivo. Chamado uma única vez, na inicialização do app.
        """
        prefs = ft.SharedPreferences()
        self._page.services.append(prefs)
        self._state.bind(prefs)
        await self._state.load_history()

    # ------------------------------------------------------------------
    # Leitura do estado atual (delegando ao Model, sempre somente-leitura)
    # ------------------------------------------------------------------
    @property
    def origin_label(self) -> str:
        return self._state.origin_label

    @property
    def origin_coords(self) -> tuple[float, float]:
        return self._state.origin_coords

    @property
    def destination(self) -> Destination | None:
        return self._state.destination

    @property
    def selected_category(self) -> RideCategory | None:
        return self._state.selected_category

    @property
    def current_driver(self):
        return self._state.current_driver

    @property
    def current_price(self) -> float:
        return self._state.current_price

    @property
    def current_duration(self) -> float:
        return self._state.current_duration

    @property
    def history(self) -> tuple[Ride, ...]:
        return self._state.history

    # ------------------------------------------------------------------
    # Origem / GPS
    # ------------------------------------------------------------------
    def create_geolocator(self) -> ftg.Geolocator:
        """
        Cria (e registra na página) o serviço de GPS. Fica no controller
        — e não dentro do Model — porque `flet_geolocator` é um detalhe de
        integração com a plataforma/UI, não uma regra de negócio.
        """
        geolocator = ftg.Geolocator()
        self._page.services.append(geolocator)
        return geolocator

    async def use_current_location(self, geolocator: ftg.Geolocator) -> tuple[float, float]:
        """
        Pede permissão de localização, lê o GPS e atualiza a origem da
        corrida no Model. Devolve as coordenadas para a View reposicionar
        o mapa e o marcador.
        """
        await geolocator.request_permission()
        position = await geolocator.get_current_position()
        coords = (position.latitude, position.longitude)
        self._state.set_origin(coords, "Minha localização atual")
        return coords

    # ------------------------------------------------------------------
    # Destino
    # ------------------------------------------------------------------
    def select_destination(self, destination: Destination) -> tuple[float, float]:
        """
        Confirma um destino (vindo de um "chip" rápido ou de um endereço já
        geocodificado) e calcula suas coordenadas a partir da origem atual.

        Se o destino já tiver uma coordenada REAL (`has_real_coordinates`,
        vinda da geocodificação de um endereço digitado), usamos ela
        diretamente e apenas recalculamos a distância até a origem atual.
        Caso contrário (um "chip" rápido, cadastrado como
        distância + direção), calculamos a coordenada com `GeoService`.
        Devolve as coordenadas para a View desenhar o marcador/rota.
        """
        if destination.has_real_coordinates:
            coords = (destination.lat, destination.lon)
            destination.distance_km = round(
                self._geo_service.haversine_distance_km(
                    *self._state.origin_coords, destination.lat, destination.lon
                ),
                1,
            )
        else:
            coords = self._geo_service.offset_point(
                *self._state.origin_coords,
                destination.distance_km,
                destination.bearing_deg,
            )
        self._state.set_destination(destination, coords)
        return coords

    async def select_destination_from_address(
        self, address: str
    ) -> tuple[Destination, tuple[float, float]]:
        """
        Resolve um endereço digitado livremente em uma coordenada REAL,
        via `AddressResolutionService` (Nominatim/OpenStreetMap), e
        confirma como destino da corrida.

        Pode levantar `AddressNotFoundError` (endereço não encontrado — a
        View deve avisar o usuário e pedir para refinar a busca).
        """
        destination = await self._address_service.resolve(address)
        coords = self.select_destination(destination)
        return destination, coords

    # ------------------------------------------------------------------
    # Categoria / preço
    # ------------------------------------------------------------------
    def price_for(self, category: RideCategory) -> tuple[float, float]:
        """Retorna `(preço estimado, duração estimada)` para uma categoria."""
        assert self._state.destination is not None
        return self._pricing_service.estimate(category, self._state.destination.distance_km)

    def confirm_category(self, category_id: str) -> RideCategory:
        """
        Confirma a categoria escolhida pelo usuário: calcula o preço final,
        sorteia o motorista e deixa tudo pronto para a tela de corrida em
        andamento (`MatchingView`).
        """
        category = find_category_by_id(category_id)
        price, duration = self.price_for(category)
        self._state.select_category(category, price, duration)
        return category

    # ------------------------------------------------------------------
    # Encerramento da corrida
    # ------------------------------------------------------------------
    async def finish_ride(self, rating: int, comment: str) -> Ride:
        """Fecha a corrida atual, salva no histórico e devolve o registro criado."""
        return await self._state.finish_ride(rating, comment)

    async def clear_history(self) -> None:
        """Apaga todo o histórico de corridas do usuário (ação irreversível)."""
        await self._state.clear_history()
