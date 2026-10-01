from dataclasses import dataclass, field


@dataclass
class CraftIngredient:
    item_id: str
    count: int


@dataclass
class CraftRecipe:
    recipe_id: str
    station: str
    level: int
    duration: int
    ingredients: list[CraftIngredient] = field(default_factory=list)
    product_id: str = ""
    product_count: int = 1
    skill: str = ""              # название навыка (напр. "Медицина")
    skill_level: int = 0         # требуемый уровень (0 = не требуется)