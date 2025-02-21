extends Control

var menu = "res://scenes/main_menu.tscn"


func _on_login_button_pressed() -> void:
	var username = $LoginContents/ButtonAndField/UsernameField.text
	if len(username) >= 2:
		SessionHandler.create_username(username)
	else:
		# CRITICAL TODO: notify user of this
		print("Username is too short.")


func _on_menu_button_pressed() -> void:
		# change the scene to the main menu
		get_tree().change_scene_to_file(menu)
