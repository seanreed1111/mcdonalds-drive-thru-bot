import json
from pathlib import Path
from typing import Self
import uuid

from pydantic import BaseModel, Field, model_validator

from enums import Size, CategoryName


class Modifier(BaseModel):
    modifier_id: str
    name: str

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Modifier):
            return NotImplemented
        return self.modifier_id == other.modifier_id and self.name == other.name

    def __hash__(self) -> int:
        return hash((self.modifier_id, self.name))


class Location(BaseModel):
    id: str
    name: str
    address: str
    city: str
    state: str
    zip: str
    country: str

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Location):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


class Item(BaseModel):
    item_id: str
    name: str
    category_name: CategoryName
    default_size: Size = Field(default=Size.REGULAR)
    size: Size | None = Field(default=None)
    quantity: int = Field(default=1, ge=1)
    modifiers: list[Modifier] = Field(
        default_factory=list
    )  # Customer selections (for orders)
    available_modifiers: list[Modifier] = Field(default_factory=list)  # Menu options

    @model_validator(mode="after")
    def set_size_from_default(self) -> Self:
        if self.size is None:
            self.size = self.default_size
        return self

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Item):
            return NotImplemented
        return (
            self.item_id == other.item_id
            and self.name == other.name
            and self.category_name == other.category_name
            and set(self.modifiers) == set(other.modifiers)
        )

    def __hash__(self) -> int:
        return hash(
            (self.item_id, self.name, self.category_name, frozenset(self.modifiers))
        )

    def _is_same_item(self, other: "Item") -> bool:
        """Check if this is the same item configuration (for ordering/addition)."""
        return (
            self.item_id == other.item_id
            and self.name == other.name
            and self.category_name == other.category_name
            and set(self.modifiers) == set(other.modifiers)
        )

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, Item) or not self._is_same_item(other):
            return NotImplemented
        return self.quantity >= other.quantity

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Item) or not self._is_same_item(other):
            return NotImplemented
        return self.quantity > other.quantity

    def __le__(self, other: object) -> bool:
        if not isinstance(other, Item) or not self._is_same_item(other):
            return NotImplemented
        return self.quantity <= other.quantity

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Item) or not self._is_same_item(other):
            return NotImplemented
        return self.quantity < other.quantity

    def __add__(self, other: object) -> "Item":
        if not isinstance(other, Item) or not self._is_same_item(other):
            return NotImplemented
        return Item(
            item_id=self.item_id,
            name=self.name,
            category_name=self.category_name,
            default_size=self.default_size,
            size=self.size,
            quantity=self.quantity + other.quantity,
            modifiers=list(self.modifiers),
            available_modifiers=list(self.available_modifiers),
        )


class Order(BaseModel):
    order_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    items: list[Item] = Field(default_factory=list)


class Menu(BaseModel):
    menu_id: str
    menu_name: str
    menu_version: str
    location: Location
    items: list[Item]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Menu):
            return NotImplemented
        return (
            self.menu_id == other.menu_id
            and self.menu_name == other.menu_name
            and self.menu_version == other.menu_version
        )

    def __hash__(self) -> int:
        return hash((self.menu_id, self.menu_name, self.menu_version))

    @classmethod
    def from_dict(cls, data: dict) -> "Menu":
        """Load Menu from a dictionary (matching JSON structure)."""
        metadata = data["metadata"]
        return cls(
            menu_id=metadata["menu_id"],
            menu_name=metadata["menu_name"],
            menu_version=metadata["menu_version"],
            location=Location(**metadata["location"]),
            items=[Item(**item) for item in data["items"]],
        )

    @classmethod
    def from_json_file(cls, path: str | Path) -> "Menu":
        """Load Menu from a JSON file path."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)
