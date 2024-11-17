import pygame

class Item:
    def __init__(self, name, weight=1, quantity=1):
        self.name = name
        self.weight = weight
        self.quantity = quantity
    
    def render(self, screen, screen_x, screen_y, scale = 0.5, color=(100, 20, 150), shape='circle', **kwargs):
        """Affiche graphiquement l'item sur l'écran avec des options de personnalisation."""
        # Convertir la position en pixels en fonction de l'échelle
        size_in_pixels = int(scale * 0.5)

        # Dessiner l'entité en fonction de la forme spécifiée
        if shape == 'circle':
            pygame.draw.circle(screen, color, (screen_x, screen_y), size_in_pixels // 2)
        elif shape == 'square':
            pygame.draw.rect(screen, color, (screen_x - size_in_pixels // 2, screen_y - size_in_pixels // 2, size_in_pixels, size_in_pixels))
        elif shape == 'triangle':
            point1 = (screen_x, screen_y - size_in_pixels // 2)
            point2 = (screen_x - size_in_pixels // 2, screen_y + size_in_pixels // 2)
            point3 = (screen_x + size_in_pixels // 2, screen_y + size_in_pixels // 2)
            pygame.draw.polygon(screen, color, [point1, point2, point3])
        # Ajouter d'autres formes si nécessaire
        else:
            raise ValueError(f"Forme non supportée: {shape}")

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
    
    def create_item(self, item_name, quantity=1):
        return Item(item_name, quantity=quantity)

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
