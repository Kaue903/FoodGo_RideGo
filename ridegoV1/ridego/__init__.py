"""
Pacote `ridego` — exercício de clone de app de mobilidade (estilo apps de
corrida), organizado no padrão MVC (Model-View-Controller) e usando
Programação Orientada a Objetos (classes, herança, encapsulamento,
abstração e polimorfismo) em toda a base de código.

Versão SIMPLIFICADA (1 arquivo por camada), pensada para facilitar o
aluno digitar o projeto do zero:

    ridego/
        model.py        -> Camada MODEL: entidades de dados (dataclasses),
                            motoristas, catálogo (categorias/destinos) e o
                            estado/regra de negócio do app (RideState).
        services.py      -> Serviços auxiliares usados pelo Model/Controller
                            (cálculo de geolocalização, precificação e
                            geocodificação de endereços).
        controller.py    -> Camada CONTROLLER: liga a View ao Model,
                            recebendo eventos da UI e decidindo o que fazer.
        views.py         -> Camada VIEW: uma classe por tela do app (todas
                            herdando de `BaseView`) + o tema visual (`Theme`).
        app.py           -> "Front controller": monta a página do Flet,
                            injeta as dependências (Model/Controller/Views)
                            e cuida do roteamento entre as telas.
"""
