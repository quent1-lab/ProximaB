import pygame, random, json
from moteurGraphique import Camera, World
from entity import Food, Animal
from PNJ import PNJ

# Charger la configuration depuis un fichier JSON
def load_config(file_path):
    with open(file_path, 'r') as f:
        config = json.load(f)
    return config

def handle_entity_hover_and_click(world, camera):
    """Gère le survol des entités par la souris et l'affichage des données de l'entité survolée."""
    mouse_x, mouse_y = pygame.mouse.get_pos()

    # Convertir la position de la souris en coordonnées du monde
    world_mouse_x = (mouse_x / camera.scale) + camera.world_offset_x
    world_mouse_y = (mouse_y / camera.scale) + camera.world_offset_y

    hovered_entity = None

    # Parcourir toutes les entités pour vérifier si la souris survole l'une d'elles
    for entity_type, entity_list in world.entities.items():
        for entity in entity_list:
            # Vérifier si la souris est sur l'entité
            if entity.x - entity.size / 2 <= world_mouse_x <= entity.x + entity.size / 2 and entity.y - entity.size / 2 <= world_mouse_y <= entity.y + entity.size / 2:
                hovered_entity = entity
                break  # On peut sortir si une entité est trouvée

    # Si une entité est survolée, afficher ses informations en haut à gauche
    if hovered_entity :
        display_entity_info(hovered_entity, camera)

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
    name = entity.__class__.__name__
    info = f"{name} at ({entity.x:.2f}, {entity.y:.2f})"
    
    # Récupérer dynamiquement tous les attributs potentiels comme énergie, faim, soif, etc.
    attributes = ["energy", "hunger", "thirst"]
    for attr in attributes:
        value = getattr(entity, attr, None)
        if value is not None:
            info += f" | {attr.capitalize()}: {value:.2f}"
    # Afficher les informations
    font = pygame.font.Font(None, 24)
    text = font.render(info, True, (255, 255, 255))
    camera.screen.blit(text, (10, 10))
    pygame.display.flip()

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

def generate_animals_in_world(world, max_animals_per_chunk=1):
    for chunk in world.loaded_chunks.values():
        for tiles in chunk.tiles:
            for tile in tiles:
                animal_count = sum(1 for tile in tiles if isinstance(tile.has_entity, Animal))
                if animal_count >= max_animals_per_chunk:
                    continue
                if tile.biome == "Plains" and random.random() < 0.0001 and not tile.has_entity:
                    animal = Animal("vache",x=tile.x, y=tile.y, world=world)
                    tile.set_entity_presence(animal)
                    world.add_entity(animal)
                    print(f"Un animal a été ajouté à la tuile {tile.x}, {tile.y}.")
                    return

def main():
    # Charger la configuration
    config = load_config('config.json')
    
    # Initialiser Pygame
    pygame.init()

    # Créer le monde et la caméra
    world = World(config)
    camera = Camera(world, config, mode="free")

    # Ajouter des PNJ avec des tailles var  iables
    pnj1 = PNJ(5, 10, world, config, id=world.generate_id(), size=1.6)  # 1.6 mètres
    pnj2 = PNJ(12, 15, world, config, id=world.generate_id(),size=1.8)  # 1.8 mètres
    #pnj1.set_target(50, 50)  # Le PNJ doit se rendre aux coordonnées (50, 50)
    world.add_entity(pnj1)
    world.add_entity(pnj2)
    
    

    # Boucle principale de simulation
    clock = pygame.time.Clock()
    running = True
    while running:
        delta_time = clock.tick(60) / 1000.0  # 60 FPS, delta_time en secondes

        # Ajouter des animaux
        generate_animals_in_world(world)
        
        # Ajouter de la nourriture
        generate_food_in_world(world)

        # Mise à jour des PNJ
        world.update_entities(delta_time)
        
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
        
        # Gérer le survol des entités par la souris
        handle_entity_hover_and_click(world, camera)

        # Gérer les événements (fermeture de la fenêtre, etc.)
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

    pygame.quit()
    
    
import threading
import time
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
        
    def initialize_simulation(self):
        """Initialiser les entités, les chunks, etc."""
        # Ajouter des entités
        pnj1 = PNJ(5, 10, self.world, self.world.config, id=self.world.generate_id(), size=1.6)
        pnj2 = PNJ(12, 15, self.world, self.world.config, id=self.world.generate_id(), size=1.8)
        
        self.world.add_entity(pnj1)
        self.world.add_entity(pnj2)

    def start_simulation(self):
        """Lancer les threads pour chaque module."""
        threading.Thread(target=self.update_entities, daemon=True).start()
        #threading.Thread(target=self.update_chunks, daemon=True).start()
        #threading.Thread(target=self.update_display, daemon=True).start()
        
        self.run_pygame()

    def update_entities(self):
        """Gérer la mise à jour des entités (par exemple, besoins vitaux)."""
        while self.is_running:
            with entity_lock:
                self.world.update_entities(self.delta_time)
                print("Updating entities...")
            time.sleep(0.01) # Cycle rapide pour les entités

    def update_chunks(self):
        """Mettre à jour les chunks (par exemple, génération de nouveaux biomes)."""
        while self.is_running:
            with chunk_lock:
                for chunk in self.world.loaded_chunks.values():
                    chunk.update_tiles()  # Par exemple, mise à jour de l'herbe ou des biomes
            time.sleep(1)  # Cycle plus lent car les chunks n'ont pas besoin de mises à jour rapides

    def update_display(self):
        """Mettre à jour le rendu graphique."""
        while self.is_running:
            # Gérer les événements (fermeture de la fenêtre, etc.)
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    self.is_running = False

            self.camera.update(self.delta_time)
            self.camera.render()
            
            time.sleep(self.delta_time)  # 60 FPS
        pygame.quit()

    def run_pygame(self):
        """Boucle principale de Pygame (doit être exécutée dans le thread principal)."""
        
        while self.is_running:
            # Gestion des événements Pygame
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE):
                    self.stop_simulation()

            # Gérer le survol des entités par la souris
            handle_entity_hover_and_click(self.world, self.camera)
            
            self.camera.update(self.delta_time)  # Mise à jour de la caméra
            self.camera.render()

            # Ajuster la vitesse de rendu (par ex., 60 FPS)
            time.sleep(1/60)

        pygame.quit()
    
    def stop_simulation(self):
        """Arrêter la simulation."""
        self.is_running = False

def main2():
    # Charger la configuration
    config = load_config('config.json')
    
    # Initialiser Pygame
    pygame.init()

    # Créer le monde et la caméra
    world = World(config, chunk_lock=chunk_lock, entity_lock=entity_lock)
    camera = Camera(world, config, mode="free")
    
    sim = Simulation(world, camera)
    sim.initialize_simulation()
    sim.start_simulation()

if __name__ == "__main__":
    main2()


