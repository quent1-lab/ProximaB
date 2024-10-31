class Item:
    def __init__(self, name, weight=1, quantity=1):
        self.name = name
        self.weight = weight
        self.quantity = quantity

    def __repr__(self):
        return f"{self.name} (x{self.quantity})"

class DroppedItem:
    def __init__(self, item, position):
        self.item = item
        self.position = position  # Position (x, y) dans le monde

    def __repr__(self):
        return f"Dropped {self.item} at {self.position}"


class Inventory:
    def __init__(self, capacity):
        self.capacity = capacity
        self.items = {}

    def add_item(self, item):
        if item.name in self.items:
            self.items[item.name].quantity += item.quantity
        else:
            self.items[item.name] = item

    def remove_item(self, item_name, quantity=1):
        if item_name in self.items:
            if self.items[item_name].quantity > quantity:
                self.items[item_name].quantity -= quantity
            else:
                del self.items[item_name]

    def has_item(self, item_name):
        return item_name in self.items

    def __repr__(self):
        return f"Inventory: {self.items}"
