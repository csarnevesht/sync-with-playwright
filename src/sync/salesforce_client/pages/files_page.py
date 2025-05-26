def upload_files(self, files_to_add):
    """Upload files to Salesforce."""
    try:
        logger.info(f"Attempting to upload {len(files_to_add)} files")
        
        # Click "Add Files" button
        add_files_button = self.page.wait_for_selector('button:has-text("Add Files")', timeout=4000)
        if not add_files_button:
            logger.error("Could not find 'Add Files' button")
            return False
        add_files_button.click()
        logger.info("Clicked 'Add Files' button")
        
        # Wait for the upload dialog
        self.page.wait_for_selector('div.modal-container', timeout=4000)
        
        # Click "Upload Files" button in the dialog
        upload_button = self.page.wait_for_selector('button:has-text("Upload Files")', timeout=4000)
        if not upload_button:
            logger.error("Could not find 'Upload Files' button in dialog")
            return False
        upload_button.click()
        logger.info("Clicked 'Upload Files' button in dialog")
        
        # Wait for file input to be ready
        file_input = self.page.wait_for_selector('input[type="file"]', timeout=4000)
        if not file_input:
            logger.error("Could not find file input element")
            return False
        
        # Set the files to upload
        file_input.set_input_files(files_to_add)
        logger.info(f"Set {len(files_to_add)} files to upload")
        
        # Wait for upload to complete
        try:
            # Wait for the progress indicator to disappear
            self.page.wait_for_selector('div.progress-indicator', timeout=2000, state='hidden')
            logger.info("File upload completed")
            
            # Wait for the success message
            self.page.wait_for_selector('div.slds-notify--success', timeout=4000)
            logger.info("Upload success message received")
            
            # Click "Done" button
            done_button = self.page.wait_for_selector('button:has-text("Done")', timeout=4000)
            if done_button:
                done_button.click()
                logger.info("Clicked 'Done' button")
            
            return True
        except Exception as e:
            logger.error(f"Error during file upload: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"Error in upload_files: {str(e)}")
        return False 