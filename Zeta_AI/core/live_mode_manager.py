"""
Gestionnaire d'état pour le mode Live
"""

class LiveModeManager:
    """Singleton pour gérer l'état global du mode Live"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.is_live_mode = False
        return cls._instance
    
    def enable_live_mode(self):
        """Active le mode Live"""
        self.is_live_mode = True
        print("🟢 Mode Live activé")
    
    def disable_live_mode(self):
        """Désactive le mode Live"""
        self.is_live_mode = False
        print("⚪ Mode Live désactivé")
    
    def get_status(self):
        """Retourne l'état actuel du mode Live"""
        return self.is_live_mode

# Exemple d'utilisation
if __name__ == "__main__":
    manager = LiveModeManager()
    print("État initial:", manager.get_status())  # False
    
    manager.enable_live_mode()
    print("État après activation:", manager.get_status())  # True
    
    manager.disable_live_mode()
    print("État après désactivation:", manager.get_status())  # False
