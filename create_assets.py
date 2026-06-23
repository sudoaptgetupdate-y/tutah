from PIL import Image, ImageDraw

def create_placeholder(path, text, color):
    img = Image.new('RGB', (800, 120), color=color)
    d = ImageDraw.Draw(img)
    # Just a simple block for now
    img.save(path)

create_placeholder('templates/default_header.png', 'Header', (26, 93, 26)) # Dark green
create_placeholder('templates/default_footer.png', 'Footer', (200, 200, 200)) # Light gray
