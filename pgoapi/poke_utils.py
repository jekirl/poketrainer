def pokemonIVPercentage(pokemon):
     return ((pokemon.get("individual_attack",0) + pokemon.get("individual_stamina",0) + pokemon.get("individual_defense",0))/45.)*100.0
