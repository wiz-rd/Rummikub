extends Control


func _on_copy_code_button_pressed() -> void:
	"""
	Copy the game "code" to the user's clipboard.
	"""
	# if the game doesn't exist
	if Globals.game_data == null:
		return
	# just another sanity check
	elif Globals.game_data.size() <= 1:
		# TODO: add better clarifications to users
		# NOTE: this should really be handled at the
		# source, in globals.gd
		return

	# if the game does exist, copy the id to clipboard
	DisplayServer.clipboard_set(Globals.game_data.id)


func _on_create_game_button_pressed() -> void:
	"""
	Attempt to create a game on the server.
	"""
	Globals.create_game()
	$ButtonsAndInput/CopyCodeButton.visible = true
	$ButtonsAndInput/CreateGameButton.visible = false

	while (Globals.game_data == null or Globals.game_data.is_empty()):
		await get_tree().create_timer(0.1).timeout
		if Globals.game_data.has("failed"):
			push_error("Game data was not saved correctly.")

	$ButtonsAndInput/GameCodeInput.text = Globals.game_data.id


func _on_join_game_button_pressed() -> void:
	"""
	Attempts to join a game.
	"""
	var game_id: String = $ButtonsAndInput/GameCodeInput.text
	var game_joined: bool = Globals.join_game(game_id)

	if game_joined:
		get_tree().change_scene_to_file(Globals.TABLE_SCENE)
	else:
		push_error("There was an issue with joining the game.")
