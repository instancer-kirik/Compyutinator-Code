import random

class Island:
    def __init__(self, name, resources, danger_level):
        self.name = name
        self.resources = resources
        self.danger_level = danger_level
        self.discovered = False
        
    def explore(self):
        self.discovered = True
        # Random chance of finding extra resources based on danger level
        if random.random() < (self.danger_level / 10):
            bonus = random.randint(1, 5)
            print(f"Lucky! You found {bonus} extra resources!")
            return self.resources + bonus
        return self.resources

class IslandGame:
    def __init__(self):
        self.islands = [
            Island("Palm Paradise", 5, 2),
            Island("Skull Island", 10, 8),
            Island("Mystery Atoll", 7, 5),
            Island("Treasure Cove", 15, 9),
            Island("Safe Haven", 3, 1)
        ]
        self.player_resources = 0
        self.current_island = None
        
    def play(self):
        print("Welcome to Island Explorer!")
        print("Try to collect resources while managing risk...")
        
        while True:
            self.show_status()
            choice = self.get_player_choice()
            
            if choice == 'q':
                print(f"\nGame Over! Final resources: {self.player_resources}")
                break
            
            # Explore chosen island
            island = self.islands[int(choice) - 1]
            print(f"\nExploring {island.name}...")
            
            # Check if danger kills player
            if random.random() < (island.danger_level / 10):
                print(f"Oh no! The dangers of {island.name} were too great!")
                print(f"Game Over! Final resources: {self.player_resources}")
                break
                
            # If survived, collect resources
            found_resources = island.explore()
            self.player_resources += found_resources
            print(f"You collected {found_resources} resources!")
            
    def show_status(self):
        print(f"\nCurrent Resources: {self.player_resources}")
        print("\nAvailable Islands:")
        for i, island in enumerate(self.islands, 1):
            discovered = "(Discovered)" if island.discovered else "(Undiscovered)"
            print(f"{i}. {island.name} {discovered}")
            if island.discovered:
                print(f"   Danger Level: {'🔥' * island.danger_level}")
                print(f"   Base Resources: {island.resources}")
    
    def get_player_choice(self):
        while True:
            choice = input("\nChoose an island to explore (1-5) or 'q' to quit: ").lower()
            if choice == 'q':
                return choice
            if choice.isdigit() and 1 <= int(choice) <= len(self.islands):
                return choice
            print("Invalid choice! Please try again.")

# Start the game
if __name__ == "__main__":
    game = IslandGame()
    game.play()