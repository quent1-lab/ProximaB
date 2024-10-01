import json
import numpy as np
import perlin_noise
from entity import Entity

# Charger la configuration depuis un fichier JSON
def load_config(file_path):
    with open(file_path, 'r') as f:
        config = json.load(f)
    return config

class PerlinNoiseGenerator:
    """Classe pour générer du bruit de Perlin."""
    def __init__(self, config):
        self.noise = perlin_noise.PerlinNoise(octaves=config['perlin']['octaves'], seed=config['perlin']['seed'])
    
    def get_noise(self, x, y, chunk_size):
        """Retourne la valeur du bruit de Perlin pour des coordonnées données."""
        nx = x / chunk_size
        ny = y / chunk_size
        return self.noise([nx, ny])

class Chunk:
    """Classe représentant un chunk de terrain."""
    def __init__(self, x_offset, y_offset, noise_generator, config):
        self.x_offset = x_offset
        self.y_offset = y_offset
        self.chunk_size = config['chunk_size']
        self.biomes = config['biomes']
        self.tiles = self.generate_chunk(noise_generator)
    
    def generate_chunk(self, noise_generator):
        """Génère un chunk avec des transitions douces entre biomes."""
        chunk = np.zeros((self.chunk_size, self.chunk_size), dtype=object)
        for x in range(self.chunk_size):
            for y in range(self.chunk_size):
                # Obtenir la valeur du bruit
                noise_value = noise_generator.get_noise(x + self.x_offset, y + self.y_offset, self.chunk_size)
                # Assigner le biome avec des transitions douces
                chunk[x][y] = self.get_biome_with_transition(noise_value)
        return chunk
    
    def get_biome_with_transition(self, value):
        """Retourne un biome avec des transitions douces entre biomes."""
        for i, biome in enumerate(self.biomes):
            if biome['min_noise_value'] <= value < biome['max_noise_value']:
                # Si on est proche d'une frontière entre deux biomes, créer une transition douce
                if i > 0 and value < biome['min_noise_value'] + 0.1:
                    # Transition avec le biome précédent
                    prev_biome = self.biomes[i - 1]
                    mix_factor = (value - biome['min_noise_value']) / 0.1
                    return self.interpolate_biomes(prev_biome['name'], biome['name'], mix_factor)
                elif i < len(self.biomes) - 1 and value > biome['max_noise_value'] - 0.1:
                    # Transition avec le biome suivant
                    next_biome = self.biomes[i + 1]
                    mix_factor = (biome['max_noise_value'] - value) / 0.1
                    return self.interpolate_biomes(biome['name'], next_biome['name'], mix_factor)
                return biome['name']
        return 'Unknown'
    
    def interpolate_biomes(self, biome1, biome2, mix_factor):
        """Mélange deux biomes en fonction du facteur de mixage."""
        if mix_factor < 0.5:
            return biome1
        else:
            return biome2

class World:
    """Classe gérant le monde et les chunks générés."""
    def __init__(self, config):
        self.noise_generator = PerlinNoiseGenerator(config)
        self.loaded_chunks = {}  # Dictionnaire stockant les chunks chargés
        self.config = config
    
    def get_chunk(self, chunk_x, chunk_y):
        """Retourne un chunk, le génère si nécessaire."""
        if (chunk_x, chunk_y) not in self.loaded_chunks:
            # Générer et stocker le chunk s'il n'existe pas encore
            self.loaded_chunks[(chunk_x, chunk_y)] = Chunk(chunk_x * self.config['chunk_size'], chunk_y * self.config['chunk_size'], self.noise_generator, self.config)
        return self.loaded_chunks[(chunk_x, chunk_y)]
    
    def load_chunks_around_camera(self, camera_x, camera_y):
        """Charge les chunks autour de la position de la caméra."""
        chunk_x = camera_x // self.config['chunk_size']
        chunk_y = camera_y // self.config['chunk_size']
        for cx in range(chunk_x - self.config['view_distance'], chunk_x + self.config['view_distance'] + 1):
            for cy in range(chunk_y - self.config['view_distance'], chunk_y + self.config['view_distance'] + 1):
                self.get_chunk(cx, cy)

class Camera:
    """Classe gérant la position de la caméra et le chargement dynamique des chunks."""
    def __init__(self, world, config, start_x=0, start_y=0):
        self.world = world
        self.x = start_x
        self.y = start_y
        self.config = config
        self.update_chunks()
    
    def move(self, dx, dy):
        """Déplace la caméra et met à jour les chunks visibles."""
        self.x += dx
        self.y += dy
        self.update_chunks()
    
    def update_chunks(self):
        """Charge les chunks autour de la nouvelle position de la caméra."""
        self.world.load_chunks_around_camera(self.x, self.y)
    
    def render(self):
        """Affiche les chunks visibles autour de la caméra."""
        chunk_x = self.x // self.config['chunk_size']
        chunk_y = self.y // self.config['chunk_size']
        for cx in range(chunk_x - self.config['view_distance'], chunk_x + self.config['view_distance'] + 1):
            for cy in range(chunk_y - self.config['view_distance'], chunk_y + self.config['view_distance'] + 1):
                chunk = self.world.get_chunk(cx, cy)
                print(f"Chunk ({cx}, {cy}):")
                print(chunk.tiles)
                print("")

# Exemple d'utilisation
def main():
    # Charger la configuration depuis un fichier JSON
    config = load_config('config.json')
    
    # Créer le monde avec la configuration
    world = World(config)
    
    # Créer la caméra avec la configuration
    camera = Camera(world, config, start_x=0, start_y=0)
    pnj = Entity(0, 0, world, config)
    
    # Déplacer la caméra pour charger des nouveaux chunks
    camera.render()  # Afficher la zone initiale
    camera.move(16, 0)  # Déplacer la caméra vers la droite
    camera.render()  # Afficher les nouveaux chunks
    
    for i in range(10):
        pnj.move(i)
        print(pnj.x, pnj.y)

if __name__ == "__main__":
    main()
