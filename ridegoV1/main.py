#
# RideGo — exercício de clone de app de mobilidade (estilo apps de corrida)
#
# Sem usar nome, logo ou marca de nenhum app real: só a experiência (pedir
# corrida, escolher categoria, acompanhar a corrida, avaliar) recriada com
# dados fictícios. Usa OpenStreetMap (flet-map) e GPS real (flet-geolocator).
#
# ---------------------------------------------------------------------------
# ARQUITETURA: MVC (Model-View-Controller) + Orientação a Objetos
# ---------------------------------------------------------------------------
# Este arquivo é só o "botão de ligar": ele entrega a página do Flet para a
# classe `App` (em `ridego/app.py`) e deixa ELA cuidar de tudo. Todo o
# resto do app vive dentro do pacote `ridego/`, organizado em 5 arquivos:
#
#   ridego/model.py       -> MODEL      (entidades + estado + regras de negócio)
#   ridego/services.py    -> auxiliares usados pelo Model/Controller
#   ridego/controller.py  -> CONTROLLER (liga a View ao Model)
#   ridego/views.py       -> VIEW       (uma classe por tela + o tema visual)
#   ridego/app.py         -> roteamento entre as telas
#
# Veja o docstring de `ridego/__init__.py` para o mapa completo do pacote.
#
import flet as ft

from ridego.app import App


async def main(page: ft.Page) -> None:
    """
    Função exigida pelo Flet como ponto de entrada de uma sessão do app.
    Toda a lógica de verdade mora na classe `App` — este `main()` só existe
    para satisfazer a assinatura que `ft.run(...)` espera.
    """
    await App(page).run()


if __name__ == "__main__":
    ft.run(main)
