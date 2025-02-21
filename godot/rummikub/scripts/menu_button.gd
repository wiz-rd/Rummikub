extends Button


func _on_pressed() -> void:
	# switch back to the main menu
	get_tree().change_scene_to_file(Globals.MENU_SCENE)
