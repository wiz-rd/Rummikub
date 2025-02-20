extends Node

var crsess = preload("res://scenes/create_session.tscn").instantiate()
var tbl = preload("res://scenes/table.tscn").instantiate()

func switch_to_create_session():
	"""
	Switches to the CreateSession node.
	"""
	get_tree().root.add_child(crsess)
