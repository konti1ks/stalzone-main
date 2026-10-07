from models import CraftRecipe


class HideoutCalculator:
    def __init__(self, items: dict[str, str], recipes: list[CraftRecipe]):
        self.items = items
        self.recipes = recipes
        self.prices: dict[str, float] = {}
        self._by_product: dict[str, list[CraftRecipe]] = {}
        for r in recipes:
            self._by_product.setdefault(r.product_id, []).append(r)

    def set_price(self, item_id: str, price: float) -> None:
        self.prices[item_id] = price

    def get_price(self, item_id: str) -> float | None:
        return self.prices.get(item_id)

    def find_recipes_for_product(self, product_id: str) -> list[CraftRecipe]:
        return list(self._by_product.get(product_id, []))

    # ============================================================
    # Стоимость ТОЛЬКО по закупочным ценам (режим "Закупка")
    # ============================================================
    def craft_cost(self, recipe: CraftRecipe,
                   _seen: set[str] | None = None) -> float:
        if _seen is None:
            _seen = set()
        if recipe.recipe_id in _seen:
            return float("inf")
        _seen.add(recipe.recipe_id)

        total = 0.0
        for ing in recipe.ingredients:
            price = self.get_price(ing.item_id)
            if price is not None:
                total += price * ing.count
            else:
                sub = self.find_recipes_for_product(ing.item_id)
                if sub:
                    best = min(
                        (self.craft_cost(r, _seen) for r in sub),
                        default=float("inf"))
                    if best == float("inf"):
                        return float("inf")
                    total += best * ing.count
                else:
                    return float("inf")
        return total

    # ============================================================
    # Себестоимость крафта (только крафт, без сравнения с закупкой)
    # ============================================================
    def craft_unit(self, item_id: str,
                   _seen: set[str] | None = None) -> float:
        """Себестоимость крафта 1 единицы предмета.
        Если рецепта нет — берём закупочную цену.
        Если ни того, ни другого — inf."""
        if _seen is None:
            _seen = set()
        if item_id in _seen:
            return float("inf")

        recipes = self.find_recipes_for_product(item_id)
        if recipes:
            new_seen = _seen | {item_id}
            best = float("inf")
            for r in recipes:
                c = self.recipe_cost_craft(r, new_seen)
                if c < best:
                    best = c
            if best != float("inf"):
                return best

        price = self.get_price(item_id)
        if price is not None:
            return price
        return float("inf")

    def recipe_cost_craft(self, recipe: CraftRecipe,
                          _seen: set[str] | None = None) -> float:
        """Себестоимость рецепта — все ингредиенты считаются по крафту."""
        if _seen is None:
            _seen = set()
        if recipe.recipe_id in _seen:
            return float("inf")
        new_seen = _seen | {recipe.recipe_id}

        total = 0.0
        for ing in recipe.ingredients:
            unit = self.craft_unit(ing.item_id, new_seen)
            if unit == float("inf"):
                return float("inf")
            total += unit * ing.count
        return total

    # ============================================================
    # Минимум (крафт или закупка) — оставлено для совместимости
    # ============================================================
    def unit_cost(self, item_id: str,
                  _seen: set[str] | None = None) -> float:
        if _seen is None:
            _seen = set()
        if item_id in _seen:
            return float("inf")

        price = self.get_price(item_id)
        recipes = self.find_recipes_for_product(item_id)

        craft = float("inf")
        if recipes:
            new_seen = _seen | {item_id}
            for r in recipes:
                c = self.recipe_cost_craft(r, new_seen)
                if c < craft:
                    craft = c

        if price is None and craft == float("inf"):
            return float("inf")
        if price is None:
            return craft
        if craft == float("inf"):
            return price
        return min(price, craft)

    # ============================================================
    # Детализация
    # ============================================================
    def recipe_details(self, recipe: CraftRecipe,
                       mode: str = "buy") -> list[dict]:
        """
        mode="buy"   — только закупочные цены
        mode="craft" — только крафт (для тех у кого есть рецепт)
        """
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
                "craft_unit": None,
                "buy_unit": None,
                "used_craft": False,
                "has_recipe": bool(sub_recipes),
            }

            if mode == "buy":
                if price is not None:
                    row["line_total"] = price * ing.count
                    row["buy_unit"] = price

            elif mode == "craft":
                # для крафта: если есть рецепт — считаем только крафт
                if sub_recipes:
                    seen = {recipe.recipe_id}
                    best = float("inf")
                    for r in sub_recipes:
                        c = self.recipe_cost_craft(r, seen)
                        if c < best:
                            best = c
                    if best != float("inf"):
                        row["line_total"] = best * ing.count
                        row["craft_unit"] = best
                        row["used_craft"] = True
                        row["buy_unit"] = price
                        rows.append(row)
                        continue

                # если рецепта нет (или крафт не посчитать) — берём закупку
                if price is not None:
                    row["line_total"] = price * ing.count
                    row["buy_unit"] = price

            rows.append(row)
        return rows

    def recipe_cost(self, recipe: CraftRecipe,
                    mode: str = "buy") -> float | None:
        total = 0.0
        for row in self.recipe_details(recipe, mode=mode):
            if row["line_total"] is None:
                return None
            total += row["line_total"]
        return total