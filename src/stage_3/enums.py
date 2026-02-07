from enum import StrEnum


class Size(StrEnum):
    SNACK = "snack"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    REGULAR = "regular"


class CategoryName(StrEnum):
    BREAKFAST = "breakfast"
    BEEF_PORK = "beef-pork"
    CHICKEN_FISH = "chicken-fish"
    SALADS = "salads"
    SNACKS_SIDES = "snacks-sides"
    DESSERTS = "desserts"
    BEVERAGES = "beverages"
    COFFEE_TEA = "coffee-tea"
    SMOOTHIES_SHAKES = "smoothies-shakes"
