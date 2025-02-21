extends Control


func _on_login_button_pressed() -> void:
	var username = $LoginContents/ButtonAndField/UsernameField.text
	if len(username) >= 2:
		SessionHandler.create_username(username)
	else:
		# CRITICAL TODO: notify user of this
		print("Username is too short.")
