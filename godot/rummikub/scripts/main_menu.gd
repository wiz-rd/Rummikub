extends Control

var crsess = "res://scenes/create_session.tscn"
var tbl = "res://scenes/table.tscn"
var attr = "res://scenes/attributions.tscn"


func _on_start_button_pressed() -> void:
	if SessionHandler.username == null or SessionHandler.username == "":
		# change the scene to CreateSession
		get_tree().change_scene_to_file(crsess)
	else:
		# change the scene to Table
		# TODO: change this to the CreateGame
		# scene AND CRITICAL add logic to the
		# CreateGame scene to, if the user is already
		# in a game they try and join, reopen said game.
		get_tree().change_scene_to_file(tbl)


func _on_attributions_button_pressed() -> void:
	SessionHandler.get_username()
	#get_tree().change_to_scene_file(attr)


func _on_ready() -> void:
	# once this site loads, get the username
	# if they have one. This should, hopefully,
	# prevent the need to wait for the server to respond
	# when they click start
	SessionHandler.get_username()
