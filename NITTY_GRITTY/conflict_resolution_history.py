class ConflictResolutionHistory:
    
    #so this should be considered carefully as to what "is" a resolution
    #it could be as simple as a boolean of whether the merge conflict was resolved or not
    #or it could be a more complex description of the resolution
    #or it could be a merge suggestion
    #or it could be a AI generated merge suggestion
    #or it could be a human generated merge suggestion
    #or it could be a combination of these things
    #or it could be a resolution that is part of a larger pattern
    #or it could be a resolution that is part of a smaller pattern
    #maybe to skip steps, and suggest later iteration
       def record_resolution(self, conflict, resolution):
           # Record how a specific conflict was resolved
           pass

       def get_similar_past_resolutions(self, conflict):
           # Retrieve similar past resolutions to guide current merge
           pass