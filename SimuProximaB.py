import pygame, random, json, threading, time
from moteurGraphique import Camera, World
from entity import Food, Animal
from PNJ import PNJ
from event import EventManager

# Charger la configuration depuis un fichier JSON
def load_config(file_path):
    with open(file_path, 'r') as f:
        config = json.load(f)
    return config

def handle_entity_hover_and_click(world, camera):
    """Gère le survol des entités par la souris et l'affichage des données de l'entité survolée."""
    mouse_x, mouse_y = pygame.mouse.get_pos()

    # Convertir la position de la souris en coordonnées du monde
    world_mouse_x = mouse_x / camera.scale + camera.camera_center_x - camera.screen_width / 2 / camera.scale
    world_mouse_y = mouse_y / camera.scale + camera.camera_center_y - camera.screen_height / 2 / camera.scale

    hovered_entity = None

    # Parcourir toutes les entités pour vérifier si la souris survole l'une d'elles
    for entity_list in world.entities.values():
        for entity in entity_list:
            # Vérifier si la souris est sur l'entité
            if entity.x - entity.size / 2 <= world_mouse_x <= entity.x + entity.size / 2 and entity.y - entity.size / 2 <= world_mouse_y <= entity.y + entity.size / 2:
                hovered_entity = entity
                break  # On peut sortir si une entité est trouvée

    # Si une entité est survolée, afficher ses informations en haut à gauche
    if hovered_entity :
        #display_entity_info(hovered_entity, camera)

        # Si un clic gauche est détecté, centrer la caméra sur l'entité
        if pygame.mouse.get_pressed()[0]:
            camera.mode = "follow"
            camera.set_mode("follow", target_pnj=hovered_entity)
            
    if camera.mode == "follow":
        display_entity_info(camera.target_pnj, camera)
        
        # Si un clic droit est détecté, arrêter de suivre le PNJ
        if pygame.mouse.get_pressed()[2]:
            camera.mode = "free"

def display_entity_info(entity, camera):
    """Affiche les informations d'une entité survolée."""
    name = entity.name
    info = f"PNJ {name} - ({entity.x:.2f}, {entity.y:.2f})"
    
    # Récupérer dynamiquement tous les attributs potentiels comme énergie, faim, soif, etc.
    for need, value in entity.needs.items():
        info += f" {need.capitalize()}: {value:.2f}"
    
    # Afficher les informations
    font = pygame.font.Font(None, 24)
    text = font.render(info, True, (255, 255, 255))
    camera.screen.blit(text, (10, 10))
    #pygame.display.flip()

def generate_food_in_world(world, max_food_per_chunk=5):
    for chunk in world.loaded_chunks.values():
        for tiles in chunk.tiles:
            for tile in tiles:
                food_count = sum(1 for tile in tiles if isinstance(tile.has_entity, Food))
                if food_count >= max_food_per_chunk:
                    continue
                if tile.biome == "Forest" and random.random() < 0.0001 and not tile.has_entity:
                    fruit = Food("Pomme", nutrition_value=20, x=tile.x, y=tile.y, world=world)
                    tile.set_entity_presence(fruit)
                    world.add_entity(fruit)
                    print(f"Une pomme a été ajoutée à la tuile {tile.x}, {tile.y}.")
                    return

def generate_animals_in_world(world, max_animals_per_chunk=2, radius=1):
    entity_positions = [(entity.x, entity.y) for entity_list in world.entities.values() for entity in entity_list]
    chunk_list = []
    
    # Récupère les chunk ou au moins un pnj est présent
    for entity in world.entities["PNJ"]:
        chunk = world.get_chunk_from_position(entity.x, entity.y)
        if chunk not in chunk_list:
            chunk_list.append(chunk)
    
    # Ajoute les chunk adjacent dans un rayon de 1
    for chunk in chunk_list.copy():
        adjacent_chunks = world.get_chunks_around(chunk.x_offset, chunk.y_offset, radius)
        for adjacent_chunk in adjacent_chunks:
            if adjacent_chunk not in chunk_list:
                chunk_list.append(adjacent_chunk)
    
    # Parcours les chunk pour ajouter des animaux
    for chunk in chunk_list:
        count = chunk.entity_count.get("animal", 0)
        if count >= max_animals_per_chunk:
            continue

        # Génère une position aléatoire dans le chunk
        x = random.randint(chunk.x_offset, chunk.x_offset + chunk.chunk_size - 1)
        y = random.randint(chunk.y_offset, chunk.y_offset + chunk.chunk_size - 1)
        
        tile = chunk.tiles[x - chunk.x_offset][y - chunk.y_offset]
        
        # Vérifie si la position est déjà occupée par une entité et que la tuile est de type "Plaine"
        if (x, y) not in entity_positions and tile.biome == "Plains":
            animal = Animal("vache",  x=x, y=y, world=world)
            #tile.set_entity_presence(animal)
            world.add_entity(animal)
            return

class PerformanceMonitor:
    def __init__(self):
        self.timings = {}
        self.thresholds = {}
        self.display = False

    def start(self, system_name):
        """Démarre la mesure de temps pour un système spécifique."""
        self.timings[system_name] = time.perf_counter()

    def stop(self, system_name):
        """Arrête la mesure de temps et calcule le temps écoulé."""
        if system_name in self.timings:
            elapsed_time = time.perf_counter() - self.timings[system_name]
            self.timings[system_name] = elapsed_time
            self.display_status(system_name, elapsed_time)
            return elapsed_time
        else:
            raise ValueError(f"Aucune mesure démarrée pour {system_name}")

    def set_threshold(self, system_name, threshold):
        """Définit un seuil au-delà duquel le système est considéré comme ralenti."""
        if threshold < 0:
            raise ValueError("Le seuil doit être supérieur à 0.")
        self.thresholds[system_name] = threshold

    def is_slow(self, system_name):
        """Vérifie si un système est au-dessus de son seuil."""
        if system_name in self.timings and system_name in self.thresholds:
            return self.timings[system_name] > self.thresholds[system_name]
        return False

    def set_display(self, display):
        """Active ou désactive l'affichage de l'état des systèmes surveillés."""
        self.display = display
    
    def display_status(self, system_name, elapsed_time):
        """Affiche l'état d'un système surveillé."""
        if not self.display:
            return
        status = "Ralentissement détecté" if self.is_slow(system_name) else "Fonctionnement normal"
        print(f"Système: {system_name} | Temps écoulé: {elapsed_time:.2f} s | État: {status}")
    
    def get_elapsed_time(self, system_name):
        """Récupère le temps écoulé pour un système spécifique."""
        if system_name == "all":
            return self.timings
        return self.timings.get(system_name, 0)

# Gestion des verrous pour éviter les conflits sur les accès aux données partagées
chunk_lock = threading.Lock()
entity_lock = threading.Lock()

# Exemple de gestionnaire de threads
class Simulation:
    def __init__(self, world, camera):
        self.world = world
        self.camera = camera
        self.delta_time = 1/60
        self.is_running = True
        
        self.monitor = PerformanceMonitor()
        self.event_manager = world.event_manager
        
    def initialize_simulation(self):
        """Initialiser les entités, les chunks, etc."""
        # Ajouter des entités
        pnj1 = PNJ(5, 10, self.world, size=1.6)
        self.world.add_entity(pnj1)
        pnj2 = PNJ(12, 15, self.world, size=1.8)
        self.world.add_entity(pnj2)

    def start_simulation(self):
        """Lancer les threads pour chaque module."""
        threading.Thread(target=self.update_entities, daemon=True).start()
        threading.Thread(target=self.update_chunks, daemon=True).start()
        #threading.Thread(target=self.update_display, daemon=True).start()
        
        self.run_pygame()

    def update_entities(self):
        """Gérer la mise à jour des entités (par exemple, besoins vitaux)."""
        delta_time = 0.05
        self.monitor.set_threshold('update_entities', delta_time * 2)
        while self.is_running:
            self.monitor.start('update_entities')
            with entity_lock:
                self.world.update_entities(delta_time)
            time.sleep(delta_time) # Cycle rapide pour les entités
            elapsed_time = self.monitor.stop('update_entities')

    def update_chunks(self):
        """Mettre à jour les chunks (par exemple, génération de nouveaux biomes)."""
        delta_time = 1
        self.monitor.set_threshold('update_chunks', delta_time * 2)
        while self.is_running:
            self.monitor.start('update_chunks')
            generate_animals_in_world(self.world)
            time.sleep(1)  # Cycle plus lent car les chunks n'ont pas besoin de mises à jour rapides
            elapsed_time = self.monitor.stop('update_chunks')
            print(f"Chunks mis à jour en {elapsed_time:.2f} s")

    def run_pygame(self):
        """Boucle principale de Pygame (doit être exécutée dans le thread principal)."""
        self.monitor.set_threshold('MoteurGraphique', self.delta_time * 2)
        
        while self.is_running:
            self.monitor.start('MoteurGraphique')
            # Gestion des événements Pygame
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE):
                    self.stop_simulation()

            self.camera.update(self.delta_time)  # Mise à jour de la caméra
            self.camera.render()
            
            # Gérer le survol des entités par la souris
            handle_entity_hover_and_click(self.world, self.camera)
            
            pygame.display.flip()
            # Ajuster la vitesse de rendu (par ex., 60 FPS)
            time.sleep(self.delta_time)
            elapsed_time = self.monitor.stop('MoteurGraphique')

        pygame.quit()
    
    def stop_simulation(self):
        """Arrêter la simulation."""
        self.is_running = False

import cProfile
import pstats

def main2():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Charger la configuration
    config = load_config('config.json')
    
    # Initialiser Pygame
    pygame.init()

    # Créer le manager d'événements
    event_manager = EventManager()
    
    # Créer le monde et la caméra
    world = World(config, chunk_lock=chunk_lock, entity_lock=entity_lock, event_manager=event_manager)
    camera = Camera(world, config, mode="free")
    
    sim = Simulation(world, camera)
    sim.initialize_simulation()
    sim.start_simulation()
    
    world.save_chunks_to_file()

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats(pstats.SortKey.TIME)
    #stats.print_stats()

if __name__ == "__main__":
    main2()


