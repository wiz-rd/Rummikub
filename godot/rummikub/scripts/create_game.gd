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
	await Globals.game_data
	$ButtonsAndInput/CopyCodeButton.visible = true
	$ButtonsAndInput/CreateGameButton.visible = false
