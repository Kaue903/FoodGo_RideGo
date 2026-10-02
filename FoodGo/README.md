# FoodGo 🍔📍 — exercício de clone de app de delivery (estilo Keeta/iFood)

Este é um **exercício de estudo**: recria a experiência de um app de delivery
(splash screen, lista de restaurantes, cardápio, carrinho, checkout e
histórico de pedidos) com **dados fictícios**. Nenhum nome, logo ou marca de
app real é usado.

## Arquitetura: MVC enxuto (poucos arquivos, didático)

Esta versão foi organizada no padrão **MVC (Model-View-Controller)** com o
**mínimo de arquivos possível**, ideal para um aluno digitar/estudar: só
**4 arquivos `.py`** no total, um para cada responsabilidade.

```
FoodGo/
├── main.py            # Ponto de entrada: monta o Controller e liga o roteamento
├── models.py          # MODEL — MenuItem, Restaurant, CartLine, Order + dados fictícios
├── controller.py      # CONTROLLER — uma única classe AppController com toda a regra de negócio
├── views.py           # VIEW — tema, componentes e as 6 telas (uma classe cada)
├── assets/
│   └── logo.png       # Logo do FoodGo
└── README.md
```

## Como rodar

```bash
python -m venv venv
Windows: venv\Scripts\activate
pip install "flet[all]"
python main.py
```

Para rodar no navegador:

```bash
flet run --web main.py 
flet run --android main.py
flet run --ios main.py
```

## Como funciona a persistência local

O carrinho e os pedidos são salvos como JSON usando o serviço
[`SharedPreferences`](https://flet.dev/docs/services/sharedpreferences) do
Flet, dentro do próprio `AppController` (métodos `load`/`_save_cart`/
`_save_orders`). A gravação roda em segundo plano
(`AppController._fire_and_forget`), para não travar a interface a cada toque.

## Avisos

- Isto é um **exercício educacional**. O pagamento no checkout é só uma
  simulação (não processa cartão, Pix nem dinheiro de verdade).
- Nenhum recurso visual, nome ou marca de app real foi copiado.
