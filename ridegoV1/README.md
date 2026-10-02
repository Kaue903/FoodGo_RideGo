# RideGo 🚗📍 — exercício de clone de app de mobilidade (estilo Uber)

Exercício de estudo: recria a experiência de pedir uma corrida (digitar
endereço ou escolher destino rápido, ver o cálculo da rota, escolher
categoria e confirmar, acompanhar a corrida, avaliar o motorista) com
**dados fictícios**. Nenhum nome, logo ou marca de app real é usado. Usa o
**OpenStreetMap** de verdade (via `flet-map`) e o **GPS real** do
dispositivo (via `flet-geolocator`).

O projeto é organizado no padrão **MVC (Model-View-Controller)** e usa
**Programação Orientada a Objetos** (classes, herança, encapsulamento,
abstração e polimorfismo) em toda a base de código — veja a seção
"Arquitetura" abaixo para o detalhe de cada camada.

## Como rodar

```bash
python -m venv venv
Windows: venv\Scripts\activate
pip install "flet[all]"
pip install flet-map flet-geolocator httpx
python main.py
```

> `httpx` é usado para consultar o serviço gratuito de geocodificação do
> OpenStreetMap (Nominatim) quando você digita um endereço — veja a seção
> abaixo.

Para rodar no navegador:

```bash
flet run --web main.py 
flet run --android main.py
flet run --ios main.py
```

## Estrutura do projeto (padrão MVC, 1 arquivo por camada)

```
RideGo/
├── main.py                  # Ponto de entrada — só liga o Flet e chama App
└── ridego/
    ├── __init__.py          # Docstring explicando o mapa do pacote
    ├── model.py             # 📦 MODEL — entidades, motoristas, catálogo e RideState
    ├── services.py          # 📦 Serviços auxiliares (geo, preço, geocodificação)
    ├── controller.py        # 📦 CONTROLLER — RideController (liga View <-> Model)
    ├── views.py             # 📦 VIEW — Theme + todas as telas (Splash, Home,
    │                        #    Categories, Matching, Rate, History)
    └── app.py               # "Front controller": monta a página e roteia as Views
```

## Como funciona a persistência local

O histórico de corridas é salvo como JSON com o serviço
[`SharedPreferences`](https://flet.dev/docs/services/sharedpreferences)
(gerenciado por `RideState.bind()` / `load_history()` / `_persist_history()`
em `ridego/model.py`), então ele continua lá mesmo se você fechar e abrir
o app de novo.

## Avisos

- Isto é um **exercício educacional**. A busca de motorista, o trajeto e o
  tempo de corrida são **simulados** (não há motoristas reais nem
  roteamento real de ruas). O **endereço digitado é geocodificado de
  verdade** (via Nominatim/OpenStreetMap, gratuito); só cai num cálculo
  simulado se não houver internet no momento, e isso fica sinalizado na
  tela.
- Nenhum recurso visual, nome ou marca de app real (Uber ou qualquer
  concorrente) foi copiado — categorias, destinos, motoristas e preços são
  todos fictícios.
- Os créditos do mapa ("© OpenStreetMap contributors") aparecem no app
  pois são exigidos pela licença de uso dos mapas — não remova essa
  atribuição se for reaproveitar este código.
