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

    def generate_tiles(self):
        """Génère les tuiles du chunk (placeholder, remplacez par votre logique de génération)."""
        return [[0 for _ in range(self.world.config['chunk_size'])] for _ in range(self.world.config['chunk_size'])]
    
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
        chunk_x = int(camera_x) // self.config['chunk_size']
        chunk_y = int(camera_y) // self.config['chunk_size']
        for cx in range(chunk_x - self.config['view_distance'], chunk_x + self.config['view_distance'] + 1):
            for cy in range(chunk_y - self.config['view_distance'], chunk_y + self.config['view_distance'] + 1):
                self.get_chunk(cx, cy)
    
    def is_within_bounds(self, x, y):
        """Vérifie si les coordonnées (x, y) sont dans les limites du monde généré."""
        # Si le monde est théoriquement infini (généré à la demande), tout est dans les limites
        return True  # On considère que les coordonnées sont toujours valides

class Camera:
    """Classe gérant la caméra comme entité invisible et fixe, les chunks se déplacent autour d'elle."""
    def __init__(self, world, config, mode="free", start_x=0, start_y=0):
        self.world = world
        self.x = start_x
        self.y = start_y
        self.world_offset_x = 0
        self.world_offset_y = 0
        self.mode = mode
        self.config = config
        self.target_pnj = None  # PNJ à suivre
        self.screen_width = config['screen_width']
        self.screen_height = config['screen_height']
        self.camera_center_x = self.screen_width // 2  # Caméra centrée horizontalement
        self.camera_center_y = self.screen_height // 2  # Caméra centrée verticalement
        self.scale = config['scale']  # Échelle initiale (zoom de base)
        self.zoom_speed = 0.5 # Vitesse de zoom
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
    
    def set_mode(self, mode, target_pnj=None):
        """Définit le mode de la caméra (fixe, libre ou suivi d'un PNJ)."""
        self.mode = mode
        if mode == "follow":
            self.target_pnj = target_pnj
    
    def update(self, delta_time):
        """Met à jour le zoom dynamique et le déplacement des chunks pour donner l'effet de mouvement."""
        self.handle_zoom()

        if self.mode == "free":
            # Les chunks se déplacent en fonction des touches pressées
            dx, dy = 0, 0
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT]:
                dx = -1.0 * self.config['camera_speed'] * delta_time
            if keys[pygame.K_RIGHT]:
                dx = 1.0 * self.config['camera_speed'] * delta_time
            if keys[pygame.K_UP]:
                dy = -1.0 * self.config['camera_speed'] * delta_time
            if keys[pygame.K_DOWN]:
                dy = 1.0 * self.config['camera_speed'] * delta_time
            self.move(dx, dy)    
        elif self.mode == "follow":
            # Suivre la position du PNJ
            self.world_offset_x = self.target_pnj.x - self.camera_center_x / self.scale
            self.world_offset_y = self.target_pnj.y - self.camera_center_y / self.scale
            self.update_chunks()
        

    def move(self, dx, dy):
        """Déplace le monde en fonction du déplacement de la caméra."""
        self.world_offset_x += dx / self.scale
        self.world_offset_y += dy / self.scale
        self.update_chunks()
    
    def update_chunks(self):
        """Charge les chunks autour de la position actuelle de la caméra."""
        camera_world_x = self.camera_center_x / self.scale + self.world_offset_x
        camera_world_y = self.camera_center_y / self.scale + self.world_offset_y
        self.world.load_chunks_around_camera(camera_world_x, camera_world_y)

    def handle_zoom(self):
        """Gère le zoom dynamique avec la molette de la souris."""
        zoom_in = pygame.mouse.get_pressed()[0]  # Bouton gauche pour zoom avant
        zoom_out = pygame.mouse.get_pressed()[2]  # Bouton droit pour zoom arrière
        
        if zoom_in:
            self.scale += self.zoom_speed
        if zoom_out and self.scale > self.zoom_speed:  # Empêcher un zoom trop petit
            self.scale -= self.zoom_speed
    
    def render(self):
        """Affiche le monde et les PNJ avec déplacement du décor en fonction de la caméra."""
        self.screen.fill((135, 206, 235))  # Fond bleu ciel

        # Afficher les chunks
        for chunk_coords, chunk in self.world.loaded_chunks.items():
            self.render_chunk(chunk)

        # Afficher les PNJ
        for pnj in self.world.pnj_list:
            screen_x = (pnj.x - self.world_offset_x) * self.scale
            screen_y = (pnj.y - self.world_offset_y) * self.scale
            self.render_pnj(screen_x, screen_y)

        pygame.display.flip()

    def render_chunk(self, chunk):
        """Affiche un chunk avec déplacement en fonction de la caméra."""
        for x in range(chunk.chunk_size):
            for y in range(chunk.chunk_size):
                tile_type = chunk.tiles[x][y]
                screen_x = int((chunk.x_offset + x - self.world_offset_x) * self.scale)
                screen_y = int((chunk.y_offset + y - self.world_offset_y) * self.scale)

                # Déterminer la couleur en fonction du biome
                if tile_type == 'Plains':
                    color = (34, 139, 34)
                elif tile_type == 'Mountains':
                    color = (139, 137, 137)
                elif tile_type == 'Water':
                    color = (65, 105, 225)
                elif tile_type == 'Beach':
                    color = (238, 214, 175)
                else:
                    color = (0, 100, 0)

                pygame.draw.rect(self.screen, color, pygame.Rect(screen_x, screen_y, self.scale, self.scale))

        # Afficher les bordures des chunks
        chunk_border_color = (255, 255, 255)
        pygame.draw.rect(self.screen, chunk_border_color, 
                         pygame.Rect((chunk.x_offset - self.world_offset_x) * self.scale, 
                                     (chunk.y_offset - self.world_offset_y) * self.scale, 
                                     chunk.chunk_size * self.scale, chunk.chunk_size * self.scale), 1)

    def render_pnj(self, screen_x, screen_y):
        """Affiche un PNJ avec un décalage par rapport à la caméra."""

        # Dessiner le PNJ comme un cercle ou une autre forme
        pygame.draw.circle(self.screen, (255, 0, 0), (screen_x, screen_y), int(self.scale // 2))

def main():
    # Charger la configuration
    config = load_config('config.json')
    
    # Initialiser Pygame
    pygame.init()

    # Créer le monde et la caméra
    world = World(config)
    camera = Camera(world, config, mode="free")

    # Ajouter des PNJ avec des tailles var  iables
    pnj1 = PNJ(10, 10, world, config, size=1.6)  # 1.6 mètres
    pnj2 = PNJ(12, 10, world, config, size=1.8)  # 1.8 mètres
    pnj1.set_target(50, 50)  # Le PNJ doit se rendre aux coordonnées (50, 50)
    world.add_pnj(pnj1)
    world.add_pnj(pnj2)

    # Boucle principale de simulation
    clock = pygame.time.Clock()
    running = True
    while running:
        delta_time = clock.tick(60) / 1000.0  # 60 FPS, delta_time en secondes

        # Mise à jour des PNJ
        world.update_pnj(delta_time)
        
        pnj1.move(delta_time)
        
        # Changer le mode de la caméra selon l'input
        keys = pygame.key.get_pressed()
        if keys[pygame.K_KP1] and camera.mode != "fixed":
            print("Mode fixe")
            camera.set_mode("fixed")
        elif keys[pygame.K_KP2] and camera.mode != "free":
            print("Mode libre")
            camera.set_mode("free")
        elif keys[pygame.K_KP3] and camera.mode != "follow":
            print("Mode follow")
            camera.set_mode("follow", target_pnj=pnj1)
        # Mise à jour de la caméra
        camera.update(delta_time)

        # Rendu de la caméra
        camera.render()

        # Gérer les événements (fermeture de la fenêtre, etc.)
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

    pygame.quit()

if __name__ == "__main__":
    main()

