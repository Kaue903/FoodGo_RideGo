"""
models.py — camada MODEL do padrão MVC.

Um único arquivo com TODAS as entidades de domínio do FoodGo (dados +
as pequenas regras de negócio que pertencem só a elas, como uma
CartLine saber calcular seu próprio total) e os dados fictícios de
restaurantes usados no app.

Estas classes NÃO desenham nada na tela (isso é papel de `views.py`) e
NÃO sabem ler/gravar arquivos ou SharedPreferences (isso é papel de
`controller.py`) — essa separação de responsabilidades é a ideia
central do MVC.

"""
from dataclasses import dataclass, field


@dataclass
class MenuItem:
    """Um item do cardápio de um restaurante (ex.:'Pizza Margherita')."""

    id: str             # Identificador único item
    name: str           # Nome exibido para o usuário
    description: str    # Descrição curta
    price: float        # Preço unitário
    emoji: str          # emoji usado como "imagem"


@dataclass
class Restaurant:
    """Um restaurante fictício, com seu cardápio de MenuItem."""

    id: str
    name: str
    category: str
    emoji: str
    rating: float
    delivery_time: str
    delivery_fee: float
    menu: list[MenuItem] = field(default_factory=list)
    #Par de cores usado no gradiente
    #aparece na miniatura da lista e no banner da tela do cardápio
    # da um identidade visual para cada categoria
    banner_colors: tuple[str, str] = ("#F9800", "#FF5252")

    def find_item(self, item_id: str) -> MenuItem | None:
        """Procura um item do cardápio pelo id. Retorna None se não achar."""
        return next((m for m in self.menu if m.id == item_id), None)


@dataclass
class CartLine:
    """Uma linha do carrinho: um item de um restaurante + a quantidade
    escolhida pelo usuário. Guardamos nome/preço/emoji "congelados" aqui
    (em vez de só o id) para o carrinho continuar funcionando mesmo que o
    cardápio mude depois."""

    restaurant_id: str
    item_id: str
    name: str
    price: float
    emoji: str
    qty: int

    @property
    def line_total(self) -> float:
        """Preço total desta linha (preço unitário x quantidade)."""
        return round(self.price * self.qty, 2)

    def to_dict(self) -> dict:
        """Converte para dicionário simples, usado para salvar em JSON."""
        return{
            "restaurant_id": self.restaurant_id,
            "item_id": self.item_id,
            "name": self.name,
            "price": self.price,
            "emoji": self.emoji,
            "qty": self.qty,
        }
    
    @staticmethod
    def from_dict(d: dict) -> "CartLine":
        """Reconstrói uma CartLine a partir do dicionário salvo em JSON."""
        return CartLine(**d)


@dataclass
class Order:
    """Um pedido já finalizado (histórico), criado a partir do carrinho
    no momento em que o usuário confirma o checkout."""

    id: str
    restaurant_name: str
    items: list[dict]
    subtotal: float
    delivery_fee: float
    total: float
    address: str
    payment: str
    created_at: str
    status: str = "Em preparo"

    def to_dict(self) -> dict:
        """Converte para dicionário somples, usado para salvar em JSON."""
        return {
            "id": self.id,
            "restaurant_name": self.restaurant_name,
            "items": self.items,
            "subtotal": self.subtotal,
            "delivery_fee": self.delivery_fee,
            "total": self.total,
            "address": self.address,
            "payment": self.payment,
            "created_at": self.created_at,
            "status": self.status,
        }
    
    @staticmethod
    def from_dict(d: dict) -> "Order":
        """Reconstrói um order a partir do dicionário salvo em JSON."""
        return Order(**d)

    
#-------------------------------------------------------------------------
#Dados fictícios (mock) usados no app - nenhuma marca real é usada
#Em app real isso viria de uma API
#Aqui é só uma fonte
#-------------------------------------------------------------------------
RESTAURANTS: list[Restaurant] = [
    Restaurant(
        id="r1",
        name="Pizzaria Bella Massa",
        category="Pizza",
        emoji="🍕",
        rating=4.7,
        delivery_time="25-35 min",
        delivery_fee=6.90,
        banner_colors=("#FF9F45", "#FF5E62"),
        menu=[
            MenuItem("m1", "Pizza Margherita", "Molho de tomate, muçarela e manjericão", 42.90, "🍕"),
            MenuItem("m2", "Pizza Calabresa", "Calabresa fatiada, cebola e azeitona", 45.90, "🍕"),
            MenuItem("m3", "Pão de alho", "6 unidades gratinadas", 14.90, "🧄"),
        ],
    ),
    Restaurant(
        id="r2",
        name="Burguer House",
        category="Hambúrguer",
        emoji="🍔",
        rating=4.5,
        delivery_time="20-30 min",
        delivery_fee=5.50,
        banner_colors=("#FFB74D", "#E65100"),
        menu=[
            MenuItem("m4", "Cheeseurguer Clássico", "Carne, queijo, alface e tomate", 28.90, "🍔"),
            MenuItem("m5", "Duplo bacon", "Dois hambúrgueres, bacon e cheddar", 36.90, "🥓"),
            MenuItem("m6", "Batata frita grande", "Porção para compartilhar", 16.90, "🍟"),
        ],
    ),
    Restaurant(
        id="r3",
        name="Sushi Kaze",
        category="Japonesa",
        emoji="🍣",
        rating=4.8,
        delivery_time="35-45 min",
        delivery_fee=8.90,
        banner_colors=("#26C6DA", "#1565C0"),
        menu=[
            MenuItem("m7", "Combo 20 peças", "Sushis e sashimis variados", 59.90, "🍣"),
            MenuItem("m8", "Yakisoba de frango", "Macarrão oriental com legumes", 32.90, "🍜"),
            MenuItem("m9", "Hot roll (8 un)", "empanado e frito", 24.90, "🍤"),
        ],
    ),
    Restaurant(
        id="r4",
        name="Verde Vida Saladas",
        category="Saudável",
        emoji="🥗",
        rating=4.6,
        delivery_time="15-25 min",
        delivery_fee=4.90,
        banner_colors=("#9CC65", "#2E7D32"),
        menu=[
            MenuItem("m10", "Salada Caesar", "Frango grelhado, alface e croutons", 26.90, "🥗"),
            MenuItem("m11", "Bowl de quinoa", "Quinoa, legumes assados e grão-de-bico", 29.90, "🥣"),
            MenuItem("m12", "Suco detox", "Couve, limão e gengibre", 12.90, "🥤"),
        ],
    ),
    Restaurant(
        id="r5",
        name="Doce Encanto",
        category="Doces",
        emoji="🥗",
        rating=4.9,
        delivery_time="20-30 min",
        delivery_fee=5.90,
        banner_colors=("#F06292", "#8E24AA"),
        menu=[
            MenuItem("m13", "Fatia de bolo de chocolate", "Recheio de brigadeiro", 15.90, "🍫"),
            MenuItem("m14", "Cheesecake de morango", "Fatia individual", 17.90, "🍰"),
            MenuItem("m15", "Brownie com sorvete", "Brownie quente com bola de sorvete", 19.90, "🍨"),
        ],
    ),
]

