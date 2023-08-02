from PIL import Image, ImageDraw, ImageFont

def format_text(text, Nmax=30, Nmin=20):
    words = text.split()
    lines = []
    line = ""

    for word in words:
        if len(line) + len(word) <= Nmax:
            line += " " + word
        else:
            if len(line) < Nmin and len(lines) > 0:
                # Añade la palabra a la línea anterior
                lines[-1] += " " + line.strip()
                line = ""
            else:
                lines.append(line.strip())
                line = word

    # Añade la última línea si es necesario
    if line:
        lines.append(line.strip())

    # Combinar las líneas en un texto con saltos de línea
    return '\n'.join(lines)

def format_message_with_linebreaks(message, Nmax=30, Nmin=20):
    segments = message.split('\n')
    formatted_segments = [format_text(segment, Nmax, Nmin) for segment in segments]
    return '\n'.join(formatted_segments)

def generate_card(message, filename='tarjeta.png', font_path='DejaVuSans.ttf'):
    message = format_message_with_linebreaks(message)
    width, height = 480, 720
    img = Image.new('RGB', (width, height), color='black')
    draw = ImageDraw.Draw(img)

    font_size = 40
    font = ImageFont.truetype(font_path, font_size)

    # Ajusta el tamaño de la fuente para que el texto quepa
    text_bbox = draw.multiline_textbbox((0, 0), message, font=font, spacing=10)
    while text_bbox[2] > width - 40:  # text_bbox[2] es el ancho del texto
        font_size -= 1
        font = ImageFont.truetype(font_path, font_size)
        text_bbox = draw.multiline_textbbox((0, 0), message, font=font, spacing=10)

    # Centra el texto
    text_width, text_height = text_bbox[2], text_bbox[3]
    text_x = (width - text_width) / 2
    text_y = (height - text_height) / 2

    draw.multiline_text((text_x, text_y), message, font=font, fill=(255, 255, 255), spacing=10)
    
    img.save(filename)
    

