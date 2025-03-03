extends Control


func _on_login_button_pressed() -> void:
	var local_username = $LoginContents/ButtonAndField/UsernameField.text
	if len(local_username) >= 2:
		SessionHandler.create_username(local_username)
		# commenting this out for the time being because
		# not running it doesn't seem to have an adverse effect on
		# the program anyway, so this may not even be needed
		#var counter = 0
		#print("Username: '" + SessionHandler.username + "'")
		## wait on the username to be gathered
		#while not (SessionHandler.username != null and SessionHandler.username != ""):
			#SessionHandler.get_username()
			#await get_tree().create_timer(0.6).timeout
			#if counter > 10:
				## deliberately don't work. This will
				## force the user to click the "login"
				## button again and resubmit their request.
				#push_error("The server cannot be reached.")
				## CRITICAL: Notify the users of this (that they likely
				## aren't connected to the internet or the servers
				## are down)
				#counter = 0
				#return
			#counter += 1

		get_tree().change_scene_to_file(Globals.GAME_MANAGEMENT_SCENE)
	else:
		# CRITICAL TODO: notify user of this
		print("Username is too short.")
