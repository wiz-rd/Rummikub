extends Control

var crsess = preload("res://scenes/create_session.tscn").instantiate()
var tbl = preload("res://scenes/table.tscn").instantiate()


func _on_start_button_pressed() -> void:
	if SessionHandler.username == null or SessionHandler.username == "":
		# change the scene to CreateSession
		get_tree().root.add_child(crsess)
		# "remove" the main menu node
		get_tree().root.remove_child(get_node("."))
		pass
	else:
		# change the scene to Table
		get_tree().root.add_child(tbl)
		# "remove" the main menu node
		get_tree().root.remove_child(get_node("."))
		pass
