class Task:
    """Représente une tâche générique pour toute entité."""
    def __init__(self, name, action, priority, energy_cost, *args, **kwargs):
        self.name = name
        self.action = action  # Fonction/action à exécuter pour accomplir la tâche
        self.priority = priority  # Priorité de la tâche (plus élevé = plus prioritaire)
        self.energy_cost = energy_cost  # Coût en énergie de la tâche
        self.args = args
        self.kwargs = kwargs
        self.linked_tasks = []
        self.completed = False
        self.interrupted = False

    def execute(self, entity, delta_time):
        """Exécute la tâche pour une entité donnée."""
        if entity.needs["energy"] < self.energy_cost * delta_time:
            print(f"{entity} n'a pas assez d'énergie pour effectuer la tâche {self.name}.")
            self.interrupted = True
            return

        # Déduction d'énergie et exécution de l'action
        entity.needs["energy"] -= self.energy_cost * delta_time
        if self.action:
            params = (delta_time,) + self.args if self.args else (delta_time,)
            #traitement des arguments kwargs
            if self.kwargs:
                self.action(*params, **self.kwargs)
            else:
                self.action(*params)

        if self.completed:
            print(f"{entity} a terminé la tâche {self.name}.")
    
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
        #print(f"liste des tâches: {self.tasks}")

    def is_busy(self):
        """Retourne True si une tâche est en cours, False sinon."""
        return self.current_task is not None or bool(self.tasks)
    
    def set_task_completed(self):
        """Marque la tâche actuelle comme complétée."""
        if self.current_task:
            self.current_task.complete()

    def execute_tasks(self, delta_time):
        """Exécute la tâche actuelle de l'entité."""
        if not self.tasks:
            return

        # Si aucune tâche n'est en cours, on prend la première tâche disponible
        if not self.current_task:
            self.current_task = self.tasks[0]
            print(f"{self.entity} commence la tâche: {self.current_task.name}")
        else:
            if self.current_task.interrupted:
                print(f"{self.entity} a été interrompu dans la tâche: {self.current_task.name}")
                self.tasks.insert(0, self.current_task)
                self.current_task = None
                return
        
        # Si la tâche est terminée, passe à la suivante
        if self.current_task.completed:
            if self.current_task.linked_tasks:
                # Ajoute la prochaine tâche liée
                self.tasks.insert(1, self.current_task.linked_tasks.pop(0))
            self.tasks.pop(0)  # Retirer la tâche terminée
            self.current_task = None

        # Si plus aucune tâche n'est présente
        if not self.tasks:
            self.current_task = None
            return
        
        if self.current_task:
            # Exécute la tâche courante
            self.current_task.execute(self.entity, delta_time)