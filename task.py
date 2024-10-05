class Task:
    """Représente une tâche générique pour toute entité."""
    def __init__(self, name, action, priority, energy_cost, linked_tasks=None):
        self.name = name
        self.action = action  # Fonction/action à exécuter pour accomplir la tâche
        self.priority = priority  # Priorité de la tâche (plus élevé = plus prioritaire)
        self.energy_cost = energy_cost  # Coût en énergie de la tâche
        self.linked_tasks = linked_tasks if linked_tasks else []  # Autres tâches liées
        self.completed = False
        self.interrupted = False

    def execute(self, entity, delta_time):
        """Exécute la tâche pour une entité donnée."""
        entity.energy -= self.energy_cost * delta_time
        if self.action:
            self.action(entity,delta_time)  # Exécuter l'action associée à la tâche
            if self.energy_cost > entity.energy:
                print(f"{entity} n'a pas assez d'énergie pour effectuer la tâche.")
                self.interrupted = True
                return
            if self.completed:
                return
    
    def complete(self):
        """Marque la tâche comme complétée."""
        self.completed = True

class TaskManager:
    """Gestionnaire de tâches pour gérer et exécuter les tâches d'une entité."""
    def __init__(self, entity):
        self.entity = entity
        self.tasks = []  # Liste de tâches pour l'entité
        self.current_task = None

    def add_task(self, task):
        """Ajoute une tâche à la liste des tâches de l'entité."""
        self.tasks.append(task)
        self.tasks.sort(key=lambda t: t.priority, reverse=True)  # Tri par priorité

    def create_linked_tasks(self, tasks):
        """Ajoute un groupe de tâches liées."""
        for i in range(len(tasks) - 1):
            tasks[i].linked_tasks.append(tasks[i + 1])
        self.add_task(tasks[0])  # Ajouter la première tâche du groupe à la liste

    def execute_tasks(self, delta_time):
        """Exécute la tâche actuelle de l'entité."""
        if not self.tasks:
            return

        # Exécuter la première tâche de la liste
        self.current_task = self.tasks[0]
        self.current_task.execute(self.entity, delta_time)

        if self.current_task.completed:
            if self.current_task.linked_tasks:
                # Ajouter la tâche liée suivante
                print(f"{self.entity} a terminé la tâche: {self.current_task.name}")
                self.tasks.insert(0, self.current_task.linked_tasks.pop(0))
            self.tasks.pop(0)  # Retirer la tâche terminée
        
        if self.current_task.interrupted:
            self.tasks.pop(0)
            self.current_task.interrupted = False
            
        if not self.tasks:
            self.current_task = None
