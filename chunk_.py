import json
import numpy as np

# Charger la configuration depuis un fichier JSON
def load_config(file_path):
    with open(file_path, 'r') as f:
        config = json.load(f)
    return config

class Tile:
    """Représente une tuile individuelle avec des propriétés dynamiques."""
    def __init__(self, x, y, biome, config):
        self.x = x
        self.y = y
        self.biome = biome
        self.grass_quantity = 0  # Quantité d'herbe (utile pour les biomes de type plaine)
        self.has_entity = None  # Indique si un entity est présent sur la tuile
        self.entity_destination = None  # Indique si la tuile est la destination d'un entity
        self.config = config
        self.initialize_tile_properties()
    
    def initialize_tile_properties(self):
        """Initialise les propriétés en fonction du type de biome."""
        if self.biome == "plains":
            # Par exemple, les plaines peuvent avoir de l'herbe
            self.grass_quantity = self.config.get("initial_grass_quantity", 100)
        # Ajouter ici d'autres initialisations spécifiques aux biomes si nécessaire

    def set_entity_presence(self, entity_present):
        """Met à jour la présence d'un entity sur la tuile."""
        self.has_entity = entity_present
    
    def set_entity_destination(self, entity):
        """Définit cette tuile comme la destination d'un entity."""
        print(f"Entity {entity} is now moving to tile {self.x}, {self.y}")
        self.entity_destination = entity

    def update_grass_quantity(self, amount):
        """Met à jour la quantité d'herbe sur la tuile."""
        self.grass_quantity = max(0, self.grass_quantity + amount)

class Chunk:
    """Classe représentant un chunk de terrain."""
    def __init__(self, x_offset, y_offset, noise_generator, config):
        self.x_offset = x_offset
        self.y_offset = y_offset
        self.chunk_size = config['chunk_size']
        self.biomes = config['biomes']
        self.transition_zone = config.get('transition_zone', 0.2)
        self.tiles = self.generate_chunk(noise_generator, config)
    
    def generate_chunk(self, noise_generator, config):
        """Génère un chunk avec des tuiles détaillées."""
        chunk = np.zeros((self.chunk_size, self.chunk_size), dtype=object)
        for x in range(self.chunk_size):
            for y in range(self.chunk_size):
                # Obtenir la valeur du bruit
                noise_value = noise_generator.get_noise(x + self.x_offset, y + self.y_offset, self.chunk_size)
                # Assigner le biome avec des transitions douces
                biome = self.get_biome_with_transition(noise_value)
                # Créer une tuile avec les données initiales
                chunk[x][y] = Tile(x + self.x_offset, y + self.y_offset, biome, config)
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

    def get_tiles(self):
        """Renvoie les coordonnées et les tuiles du chunk."""
        for x in range(self.chunk_size):
            for y in range(self.chunk_size):
                yield x + self.x_offset, y + self.y_offset, self.tiles[x][y]


    def interpolate_biomes(self, biome1, biome2, mix_factor):
        """Mélange deux biomes en fonction du facteur de mixage."""
        if mix_factor < 0.5:
            return biome1
        else:
            return biome2
    
    def __str__(self) -> str:
        return f"Chunk at {self.x_offset}, {self.y_offset}"