"""Template management functionality."""
import os
import logging
import shutil
import jinja2

logger = logging.getLogger(__name__)

class TemplateManager:
    def __init__(self, config):
        """Initialize the template manager."""
        self.config = config
        self.template_env = self._setup_templates()

    def _setup_templates(self):
        """Set up Jinja2 template environment."""
        # Using attribute access for Pydantic models
        template_dir = self.config.templates.directory

        # Create template directory if it doesn't exist
        if not os.path.exists(template_dir):
            os.makedirs(template_dir, exist_ok=True)

            # Create default templates if they don't exist
            self._create_default_templates(template_dir)

        return jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir)
        )

    def _create_default_templates(self, template_dir):
        """Create default template files if they don't exist."""
        # Get default templates from package
        default_templates_dir = os.path.join(os.path.dirname(__file__), 'default_templates')

        # If running from a different location, try to find the default templates
        if not os.path.exists(default_templates_dir):
            try:
                # Try to find templates relative to script location
                script_dir = os.path.dirname(os.path.abspath(__file__))
                parent_dir = os.path.dirname(script_dir)
                default_templates_dir = os.path.join(parent_dir, 'default_templates')

            except:
                logger.warning("Could not locate default templates directory")

        # Copy main template
        main_template_name = self.config.templates.main_template
        main_template_path = os.path.join(template_dir, main_template_name)

        if not os.path.exists(main_template_path):
            try:
                # Try to copy from default templates
                if os.path.exists(default_templates_dir):
                    src_path = os.path.join(default_templates_dir, "paper_template.html")
                    if os.path.exists(src_path):
                        shutil.copy2(src_path, main_template_path)
                        logger.info(f"Copied default main template to {main_template_path}")
                    else:
                        self._create_empty_template(main_template_path, "Main template")
                else:
                    self._create_empty_template(main_template_path, "Main template")
            except Exception as e:
                logger.warning(f"Error creating main template: {e}")
                self._create_empty_template(main_template_path, "Main template")

        # Copy article template
        article_template_name = self.config.templates.article_template
        article_template_path = os.path.join(template_dir, article_template_name)

        if not os.path.exists(article_template_path):
            try:
                # Try to copy from default templates
                if os.path.exists(default_templates_dir):
                    src_path = os.path.join(default_templates_dir, "article_template.html")
                    if os.path.exists(src_path):
                        shutil.copy2(src_path, article_template_path)
                        logger.info(f"Copied default article template to {article_template_path}")
                    else:
                        self._create_empty_template(article_template_path, "Article template")
                else:
                    self._create_empty_template(article_template_path, "Article template")
            except Exception as e:
                logger.warning(f"Error creating article template: {e}")
                self._create_empty_template(article_template_path, "Article template")

    def _create_empty_template(self, path, template_type):
        """Create an empty template with a note about missing the default template."""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f'''<!--
{template_type} file not found.
Please create your own template or check the documentation for example templates.
-->

<html>
<head><title>Template Missing</title></head>
<body>
    <h1>Template Missing</h1>
    <p>The default template could not be found. Please create your own template or check the documentation.</p>
</body>
</html>''')
        logger.warning(f"Created empty placeholder for {template_type} at {path}")

    def get_template(self, template_name):
        """Get a template by name."""
        return self.template_env.get_template(template_name)
