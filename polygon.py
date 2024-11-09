from shapely.geometry import Polygon
import math
import functools

class PolygonOptimizer:
    def __init__(self):
        # Initialisation d'un cache pour stocker les polygones optimisés
        self.cache = {}

    def optimize_polygon(self, polygon, tolerance=0.5, angle_threshold=10):
        """
        Optimise un polygone avec mise en cache et paramètres configurables.
        """
        polygon_hash = hash(polygon.wkt)  # Utilisation du WKT pour créer un hash unique du polygone

        # Vérifier si le polygone est déjà en cache
        if polygon_hash in self.cache:
            return self.cache[polygon_hash]

        # Simplifier le polygone
        simplified_polygon = self.simplify_polygon(polygon, tolerance)

        # Supprimer les petits angles
        optimized_polygon = self.remove_small_angles(simplified_polygon, angle_threshold)

        # Stocker dans le cache
        self.cache[polygon_hash] = optimized_polygon

        return optimized_polygon

    @staticmethod
    def simplify_polygon(polygon, tolerance=0.5):
        """
        Simplifie un polygone en réduisant le nombre de sommets.
        """
        return polygon.simplify(tolerance, preserve_topology=True)

    @staticmethod
    def remove_small_angles(polygon, angle_threshold=10):
        """
        Analyse les sommets du polygone et supprime les sommets formant des angles
        trop faibles.
        """
        coords = list(polygon.exterior.coords)
        optimized_coords = []

        def angle_between_points(p1, p2, p3):
            a = math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
            b = math.sqrt((p3[0] - p2[0])**2 + (p3[1] - p2[1])**2)
            c = math.sqrt((p3[0] - p1[0])**2 + (p3[1] - p1[1])**2)
            if a == 0 or b == 0:
                return 0
            return math.degrees(math.acos((a**2 + b**2 - c**2) / (2 * a * b)))

        for i in range(len(coords)):
            p1 = coords[i - 1]
            p2 = coords[i]
            p3 = coords[(i + 1) % len(coords)]

            angle = angle_between_points(p1, p2, p3)
            if angle > angle_threshold:
                optimized_coords.append(p2)

        return Polygon(optimized_coords)

if __name__ == "__main__":
    # Exemple d'utilisation
    optimizer = PolygonOptimizer()
    polygon = Polygon([(0, 0), (1, 2), (2, 1), (3, 3), (4, 0), (0, 0)])
    optimized_polygon = optimizer.optimize_polygon(polygon, tolerance=2.0, angle_threshold=5)
    print(f"Original Polygon: {polygon}")
    print(f"Optimized Polygon: {optimized_polygon}")