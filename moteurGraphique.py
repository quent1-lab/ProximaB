import json
import pygame
import numpy as np
import perlin_noise
from entity import Entity, PNJ

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
    
    def generate_tiles(self, noise_generator):
        """Génère les types de terrain dans ce chunk en utilisant le bruit de Perlin."""
        tiles = []
        for x in range(self.chunk_size):
            row = []
            for y in range(self.chunk_size):
                noise_value = noise_generator.get_noise(self.x_offset + x, self.y_offset + y)
                if noise_value < 0.2:
                    row.append('Water')  # Zone d'eau
                elif noise_value < 0.5:
                    row.append('Plains')  # Zone de plaine
                else:
                    row.append('Mountains')  # Zone de montagnes
            tiles.append(row)
        return tiles

    def get_tile_at(self, x, y):
        """Retourne le type de terrain pour les coordonnées données."""
        chunk_x = int(x - self.x_offset)
        chunk_y = int(y - self.y_offset)
        if 0 <= chunk_x < self.chunk_size and 0 <= chunk_y < self.chunk_size:
            return self.tiles[chunk_x][chunk_y]
        return 'Unknown'  # En dehors du chunk
    
    def get_tiles(self):
        """Retourne tous les types de terrain dans ce chunk."""
        return self.tiles

class World:
    """Classe gérant le monde et les chunks générés."""
    def __init__(self, config):
        self.noise_generator = PerlinNoiseGenerator(config)
        self.loaded_chunks = {}  # Dictionnaire stockant les chunks chargés
        self.config = config
        self.pnj_list = []  # Liste des PNJ dans le monde
        self.chunks = {}  # Dictionnaire pour stocker les chunks générés

    def get_chunk(self, chunk_x, chunk_y):
        """Retourne un chunk basé sur ses coordonnées, en le générant si nécessaire."""
        if (chunk_x, chunk_y) not in self.chunks:
            # Générer un nouveau chunk s'il n'existe pas
            self.chunks[(chunk_x, chunk_y)] = Chunk(chunk_x * self.config['chunk_size'], chunk_y * self.config['chunk_size'], self.noise_generator, self.config)
        return self.chunks[(chunk_x, chunk_y)]

    def get_tile_at(self, x, y):
        """Retourne le type de terrain pour les coordonnées globales (x, y)."""
        chunk_x = int(x) // self.config['chunk_size']
        chunk_y = int(y) // self.config['chunk_size']
        chunk = self.get_chunk(chunk_x, chunk_y)
        
        # Calculer les coordonnées locales dans le chunk
        local_x = int(x) % self.config['chunk_size']
        local_y = int(y) % self.config['chunk_size']
        return chunk.tiles[local_x][local_y]
    
    def add_pnj(self, pnj):
        """Ajoute un PNJ au monde."""
        self.pnj_list.append(pnj)
    
    def update_pnj(self, delta_time):
        """Met à jour les PNJ dans le monde."""
        for pnj in self.pnj_list:
            pnj.move(delta_time)
            pnj.interact_with_other_pnj(self.pnj_list)

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
        self.screen_width = config['screen_width']
        self.screen_height = config['screen_height']
        self.scale = config['scale']  # Échelle de conversion mètres -> pixels (par ex. 1 mètre = 32 pixels)
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
    
    def move(self, dx, dy):
        """Déplace la caméra et met à jour les chunks visibles."""
        self.x += dx
        self.y += dy
        self.update_chunks()
    
    def update_chunks(self):
        """Charge les chunks autour de la nouvelle position de la caméra."""
        self.world.load_chunks_around_camera(self.x, self.y)
    
    def render(self):
        """Affiche le monde et les PNJ sur l'écran."""
        self.screen.fill((135, 206, 235))  # Couleur de fond (bleu ciel)

        # Afficher les chunks
        chunk_x = self.x // self.world.config['chunk_size']
        chunk_y = self.y // self.world.config['chunk_size']
        for cx in range(chunk_x - self.world.config['view_distance'], chunk_x + self.world.config['view_distance'] + 1):
            for cy in range(chunk_y - self.world.config['view_distance'], chunk_y + self.world.config['view_distance'] + 1):
                chunk = self.world.get_chunk(cx, cy)
                self.render_chunk(chunk)

        # Afficher les PNJ
        for pnj in self.world.pnj_list:
            pnj.render(self.screen, self.scale)

        # Mettre à jour l'affichage
        pygame.display.flip()

    def render_chunk(self, chunk):
        """Affiche un chunk à l'écran."""
        for x in range(chunk.chunk_size):
            for y in range(chunk.chunk_size):
                tile_type = chunk.tiles[x][y]
                screen_x = int((chunk.x_offset + x) * self.scale)
                screen_y = int((chunk.y_offset + y) * self.scale)
                
                # Dessiner les tuiles en fonction du type de terrain
                if tile_type == 'Plains':
                    color = (34, 139, 34)  # Vert pour les plaines
                elif tile_type == 'Mountains':
                    color = (139, 137, 137)  # Gris pour les montagnes
                elif tile_type == 'Water':
                    color = (65, 105, 225)
                elif tile_type == 'Beach':
                    color = (244, 164, 96)
                else:
                    color = (0, 100, 0)  # Vert foncé pour d'autres biomes

                pygame.draw.rect(self.screen, color, pygame.Rect(screen_x, screen_y, self.scale, self.scale))

def main():
    # Charger la configuration
    config = load_config('config.json')
    
    # Initialiser Pygame
    pygame.init()

    # Créer le monde et la caméra
    world = World(config)
    camera = Camera(world, config)

    # Ajouter des PNJ avec des tailles variables
    pnj1 = PNJ(10, 10, world, config, size=1.6)  # 1.6 mètres
    pnj2 = PNJ(12, 10, world, config, size=1.8)  # 1.8 mètres
    world.add_pnj(pnj1)
    world.add_pnj(pnj2)

    # Boucle principale de simulation
    clock = pygame.time.Clock()
    running = True
    while running:
        delta_time = clock.tick(60) / 1000.0  # 60 FPS, delta_time en secondes

        # Mise à jour des PNJ
        world.update_pnj(delta_time)

        # Rendu de la caméra
        camera.render()

        # Gérer les événements (fermeture de la fenêtre, etc.)
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

    pygame.quit()

if __name__ == "__main__":
    main()

