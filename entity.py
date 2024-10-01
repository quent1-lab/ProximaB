class Entity:
    """Classe représentant une entité physique avec des règles de physique."""
    def __init__(self, x, y, world, config):
        self.x = x
        self.y = y
        self.vx = 1  # Vitesse horizontale
        self.vy = 0  # Vitesse verticale (affectée par la gravité)
        self.world = world
        self.config = config
        self.gravity = 9.81  # Gravité (m/s^2)
        self.on_ground = False  # Indique si l'entité est au sol

    def apply_gravity(self, delta_time):
        """Applique la gravité si l'entité n'est pas au sol."""
        if not self.on_ground:
            self.vy += self.gravity * delta_time  # Appliquer la gravité
        else:
            self.vy = 0  # Si l'entité est au sol, elle ne tombe plus

    def move(self, delta_time):
        """Déplace l'entité en fonction de sa vitesse et gère les collisions."""
        self.apply_gravity(delta_time)
        
        # Calculer la nouvelle position
        new_x = self.x + self.vx * delta_time
        new_y = self.y + self.vy * delta_time
        
        # Vérifier les collisions avec le sol
        if self.collides_with_ground(new_x, new_y):
            self.on_ground = True
            self.y = self.get_ground_level(new_x, new_y)  # Placer l'entité sur le sol
        else:
            self.on_ground = False
            self.x = new_x
            self.y = new_y
    
    def collides_with_ground(self, x, y):
        """Vérifie si l'entité entre en collision avec le sol."""
        chunk_x = int(x // self.config['chunk_size'])
        chunk_y = int(y // self.config['chunk_size'])
        chunk = self.world.get_chunk(chunk_x, chunk_y)
        local_x = int(x % self.config['chunk_size'])
        local_y = int(y % self.config['chunk_size'])
        
        # Si la tuile est une montagne ou un autre biome solide, il y a collision
        return chunk.tiles[local_x][local_y] in ['Mountains', 'Solid']

    def get_ground_level(self, x, y):
        """Retourne la position Y du sol le plus proche sous l'entité."""
        chunk_x = int(x // self.config['chunk_size'])
        chunk_y = int(y // self.config['chunk_size'])
        chunk = self.world.get_chunk(chunk_x, chunk_y)
        local_x = int(x % self.config['chunk_size'])
        local_y = int(y % self.config['chunk_size'])
        for local_y in range(local_y, -1, -1):
            if chunk.tiles[local_x][local_y] in ['Mountains', 'Solid']:
                return local_y
        return y  # Si aucune collision détectée, on ne change pas la position Y
