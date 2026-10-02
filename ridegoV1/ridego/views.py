"""
`ridego.views` — a camada VIEW do padrão MVC, num único arquivo.

Cada tela do app é uma classe que herda de `BaseView` e implementa o
método `build()`. As Views só desenham a interface e encaminham eventos do
usuário para o `RideController` — nunca calculam preço, nunca acessam o
histórico diretamente, nunca decidem regra de negócio sozinhas.

Está dividido em blocos, na ordem em que um bloco depende do anterior:

1. `Theme`      — paleta de cores + componentes visuais reutilizados
2. `BaseView`   — classe abstrata da qual toda tela herda
3. `SplashView`, `HomeView`, `CategoriesView`, `MatchingView`, `RateView`,
   `HistoryView` — uma classe por tela, na ordem do fluxo do app
"""


# Digitar a partir deste ponto (Somente este arquivo)