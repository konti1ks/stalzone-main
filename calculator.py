from models import CraftRecipe


class HideoutCalculator:
    def __init__(self, items: dict[str, str], recipes: list[CraftRecipe]):
        self.items = items
        self.recipes = recipes
        self.prices: dict[str, float] = {}

    def set_price(self, item_id: str, price: float) -> None:
        self.prices[item_id] = price

    def get_price(self, item_id: str) -> float | None:
        return self.prices.get(item_id)

    def find_recipes_for_product(self, product_id: str) -> list[CraftRecipe]:
        return [r for r in self.recipes if r.product_id == product_id]

    def craft_cost(self, recipe: CraftRecipe, _seen: set[str] | None = None) -> float:
        if _seen is None:
            _seen = set()
        if recipe.recipe_id in _seen:
            return 0.0
        _seen.add(recipe.recipe_id)

        total = 0.0
        for ing in recipe.ingredients:
            price = self.get_price(ing.item_id)
            if price is not None:
                total += price * ing.count
            else:
                sub = self.find_recipes_for_product(ing.item_id)
                if sub:
                    best = min((self.craft_cost(r, _seen) for r in sub), default=0.0)
                    total += best * ing.count
        return total

    def recipe_details(self, recipe: CraftRecipe) -> list[dict]:
        rows = []
        for ing in recipe.ingredients:
            name = self.items.get(ing.item_id, ing.item_id)
            price = self.get_price(ing.item_id)
            sub_recipes = self.find_recipes_for_product(ing.item_id)

            row = {
                "item_id": ing.item_id,
                "name": name,
                "count": ing.count,
                "price": price,
                "sub_recipes": sub_recipes,
                "line_total": None,
            }
            if price is not None:
                row["line_total"] = price * ing.count
            elif sub_recipes:
                best = min((self.craft_cost(r) for r in sub_recipes), default=0.0)
                row["line_total"] = best * ing.count
            rows.append(row)
        return rows