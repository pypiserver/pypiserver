        loaded_pw_file = HtpasswdFile(self.password_file)

        # Construct a local closure over the loaded PW file and return as our
        # authentication function.
        def safe_check_password(uname: str, pw: str) -> bool:
            """Check password with error handling for invalid salt characters."""
            loaded_pw_file.load_if_changed()
            try:
                return loaded_pw_file.check_password(uname, pw)
            except ValueError as e:
                if "invalid characters in apr_md5_crypt salt" in str(e):
                    # Log the error without exposing user details
                    logging.error(f"Authentication failed: Invalid characters in password hash for a user")
                    return False
                raise

        return safe_check_password
