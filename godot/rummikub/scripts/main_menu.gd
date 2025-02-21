extends Control


func _on_start_button_pressed() -> void:
	if SessionHandler.username == null or SessionHandler.username == "":
		# change the scene to CreateSession
		get_tree().change_scene_to_file(Globals.LOGIN_SCENE)
	else:
		# change the scene to Table
		# TODO: change this to the CreateGame
		# scene AND CRITICAL add logic to the
		# CreateGame scene to, if the user is already
		# in a game they try and join, reopen said game.
		get_tree().change_scene_to_file(Globals.TABLE_SCENE)


func _on_attributions_button_pressed() -> void:
	# changing to the attributes scene
	get_tree().change_scene_to_file(Globals.ATTRIBUTES_SCENE)


func _on_ready() -> void:
	# once this site loads, get the username
	# if they have one. This should, hopefully,
	# prevent the need to wait for the server to respond
	# when they click start
	SessionHandler.get_username()
