import json
import numpy as np

# Charger la configuration depuis un fichier JSON
def load_config(file_path):
    with open(file_path, 'r') as f:
        config = json.load(f)
    return config

class Tile:
    """Représente une tuile individuelle avec des propriétés dynamiques."""
    def __init__(self, x, y, biome, config, **kwargs):
        self.x = x
        self.y = y
        self.biome = biome
        self.grass_quantity = 0
        self.has_entity = None
        self.entity_destination = None
        self.config = config
        self.__dict__.update(kwargs)
        self.chunk_lock = self.__dict__.get("chunk_lock", None)
        self.entity_lock = self.__dict__.get("entity_lock", None)
        self.initialize_tile_properties()

    def initialize_tile_properties(self):
        if self.biome == "plains":
            self.grass_quantity = self.config.get("initial_grass_quantity", 100)

    def set_entity_presence(self, entity_present):
        self.has_entity = entity_present

    def set_entity_destination(self, entity):
        print(f"Entity {entity} is now moving to tile {self.x}, {self.y}")
        self.entity_destination = entity

    def update_grass_quantity(self, amount):
        with self.chunk_lock:  # Protéger l'accès aux données des chunks
            self.grass_quantity = max(0, self.grass_quantity + amount)
    
    def to_dict(self):
        """Convertit la tuile en un dictionnaire sérialisable."""
        return {
            'x': self.x,
            'y': self.y,
            'biome': self.biome
        }

    @classmethod
    def from_dict(cls, data, config):
        """Crée une tuile à partir d'un dictionnaire sérialisé."""
        return cls(data['x'], data['y'], data['biome'], config)

class Chunk:
    """Classe représentant un chunk de terrain."""
    def __init__(self, x,y, noise_generator, config, chunk_lock=None, entity_lock=None, loaded=False):
        self.x_offset, self.y_offset = x * config['chunk_size'], y * config['chunk_size']
        self.x, self.y = x,y
        self.chunk_size = config['chunk_size']
        self.biomes = config['biomes']
        self.transition_zone = config.get('transition_zone', 0.2)
        self.entity_count = {}  # Compteur d'entités par type
        self.biome_info = {}  # Informations sur les biomes
        self.chunk_lock = chunk_lock
        self.entity_lock = entity_lock
        self.tiles = None
        self.mesh_cache = None
        
        self.dropped_items = []
        
        if not loaded:
            self.tiles = self.generate_chunk(noise_generator, config)
    
    def generate_chunk(self, noise_generator, config):
        """Génère un chunk avec des tuiles détaillées et des statistiques de biomes."""
        chunk = np.zeros((self.chunk_size, self.chunk_size), dtype=object)
        
        for x in range(self.chunk_size):
            for y in range(self.chunk_size):
                # Obtenir la valeur du bruit
                noise_value = noise_generator.get_noise(x + self.x_offset, y + self.y_offset, self.chunk_size)
                # Assigner le biome avec des transitions douces
                biome = self.get_biome_with_transition(noise_value)
                # Mettre à jour le compteur de biomes dans le chunk
                self.update_biome_info(biome, x + self.x_offset, y + self.y_offset)
                # Créer une tuile avec les données initiales
                chunk[x][y] = Tile(x + self.x_offset, y + self.y_offset, biome, config, chunk_lock=self.chunk_lock, entity_lock=self.entity_lock)
        
        return chunk
    
    def get_biome_with_transition(self, value):
        """Retourne un biome avec des transitions douces entre biomes."""
        for i, biome in enumerate(self.biomes):
            if biome['min_noise_value'] <= value < biome['max_noise_value']:
                # Transition avec les biomes voisins
                if i > 0 and value < biome['min_noise_value'] + self.transition_zone:
                    prev_biome = self.biomes[i - 1]
                    mix_factor = (value - biome['min_noise_value']) / self.transition_zone
                    return self.interpolate_biomes(prev_biome['name'], biome['name'], mix_factor)
                elif i < len(self.biomes) - 1 and value > biome['max_noise_value'] - self.transition_zone:
                    next_biome = self.biomes[i + 1]
                    mix_factor = (biome['max_noise_value'] - value) / self.transition_zone
                    return self.interpolate_biomes(biome['name'], next_biome['name'], mix_factor)
                return biome['name']
        return 'Unknown'

    def update_biome_info(self, biome_name, x=None, y=None):
        """Met à jour les infos sur les biomes regroupe les ilots de même type dans le chunk."""
        if biome_name in self.biome_info:
            # Vérifier si le biome est adjacent à un autre biome du même type
            self.biome_info[biome_name].add((x, y))
        else:
            self.biome_info[biome_name] = set()
            self.biome_info[biome_name].add((x, y))
            
    def is_adjacent_to_same_biome(self, x, y, biome_name):
        """Vérifie si une tuile est adjacente à une tuile du même type de biome."""
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        for dx, dy in directions:
            adjacent_x, adjacent_y = x + dx, y + dy
            if self.is_inside_chunk(adjacent_x, adjacent_y) and self.tiles[adjacent_x - self.x_offset][adjacent_y - self.y_offset].biome == biome_name:
                return True
        return False
    
    def is_inside_chunk(self, x, y):
        """Vérifie si les coordonnées sont à l'intérieur du chunk."""
        return 0 <= x - self.x_offset < self.chunk_size and 0 <= y - self.y_offset < self.chunk_size

    def add_entity(self, entity_type):
        """Ajoute une entité au compteur d'entités du chunk."""
        if entity_type in self.entity_count:
            self.entity_count[entity_type] += 1
        else:
            self.entity_count[entity_type] = 1
    
    def remove_entity(self, entity_type):
        """Retire une entité du compteur d'entités du chunk."""
        if entity_type in self.entity_count and self.entity_count[entity_type] > 0:
            self.entity_count[entity_type] -= 1

    def get_tiles(self):
        """Renvoie les coordonnées et les tuiles du chunk."""
        for x in range(self.chunk_size):
            for y in range(self.chunk_size):
                yield x + self.x_offset, y + self.y_offset, self.tiles[x][y]
    
    def interpolate_biomes(self, biome1, biome2, mix_factor):
        """Mélange deux biomes en fonction du facteur de mixage."""
        return biome1 if mix_factor < 0.5 else biome2
    
    def add_dropped_item(self, dropped_item):
        self.dropped_items.append(dropped_item)

    def remove_dropped_item(self, item_name, quantity=1):
        for dropped_item in self.dropped_items:
            if dropped_item.item.name == item_name:
                if dropped_item.item.quantity > quantity:
                    dropped_item.item.quantity -= quantity
                    return dropped_item
                else:
                    self.dropped_items.remove(dropped_item)
                    return dropped_item
        return None
    
    def calculate_mesh(self, greedy_mesh):
        if self.mesh_cache is not None:
            return self.mesh_cache
        self.mesh_cache = greedy_mesh(self.tiles)
        return self.mesh_cache

    def update_tile(self, x, y, new_tile):
        self.tiles[(x, y)] = new_tile
        self.mesh_cache = None  # Invalidate cache
    
    def to_dict(self):
        """Convertit le chunk en un dictionnaire sérialisable."""
        return {
            'x': self.x,
            'y': self.y,
            'tiles': [[tile.to_dict() for tile in row] for row in self.tiles],
            'biomes': {k: [list(v) for v in values] for k, values in self.biome_info.items()}  # Convertir les ensembles en listes
        }

    @classmethod
    def from_dict(cls, data, noise_generator, config, chunk_lock=None, entity_lock=None):
        """Crée un chunk à partir d'un dictionnaire sérialisé."""
        chunk = cls(data['x'], data['y'], noise_generator, config, chunk_lock, entity_lock, True)
        chunk.tiles = [[Tile.from_dict(tile_data, config) for tile_data in row] for row in data['tiles']]
        chunk.biome_info = {k: set(tuple(v) for v in values) for k, values in data['biomes'].items()}
        return chunk

    def __repr__(self):
        return f"Chunk ({self.x}, {self.y}) with items: {self.dropped_items}"
    
    def __str__(self) -> str:
        return f"Chunk {self.x_offset}, {self.y_offset}"