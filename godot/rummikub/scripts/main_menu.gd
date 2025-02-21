extends Control

var crsess = preload("res://scenes/create_session.tscn").instantiate()
var tbl = preload("res://scenes/table.tscn").instantiate()
var attr = preload("res://scenes/attributions.tscn").instantiate()


func _on_start_button_pressed() -> void:
	if SessionHandler.username == null or SessionHandler.username == "":
		# change the scene to CreateSession
		get_tree().root.add_child(crsess)
		# "remove" the main menu node
		get_node(".").hide()
		#get_tree().root.remove_child(get_node("."))
	else:
		# change the scene to Table
		# TODO: change this to the CreateGame
		# scene AND CRITICAL add logic to the
		# CreateGame scene to, if the user is already
		# in a game they try and join, reopen said game.
		get_tree().root.add_child(tbl)
		# "remove" the main menu node
		get_tree().root.remove_child(get_node("."))


func _on_attributions_button_pressed() -> void:
	SessionHandler.get_username()
	#get_tree().root.add_child(attr)
	#get_tree().root.remove_child(get_node("."))


func _on_ready() -> void:
	# once this site loads, get the username
	# if they have one. This should, hopefully,
	# prevent the need to wait for the server to respond
	# when they click start
	SessionHandler.get_username()
