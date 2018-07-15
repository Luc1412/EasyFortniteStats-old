import bs4 as bs4

import requests
from PIL import Image, ImageDraw, ImageFilter


def create_rounded_rectangle_mask(rectangle, radius):
    solid_fill = (50, 50, 50, 255)

    mask = Image.new('RGBA', rectangle.size, (0, 0, 0, 0))

    corner = Image.new('RGBA', (radius, radius), (0, 0, 0, 0))
    draw = ImageDraw.Draw(corner)
    draw.pieslice((0, 0, radius * 2, radius * 2), 180, 270, fill=solid_fill)

    mx, my = rectangle.size

    mask.paste(corner, (0, 0), corner)
    mask.paste(corner.rotate(90), (0, my - radius), corner.rotate(90))
    mask.paste(corner.rotate(180), (mx - radius, my - radius), corner.rotate(180))
    mask.paste(corner.rotate(270), (mx - radius, 0), corner.rotate(270))

    draw = ImageDraw.Draw(mask)
    draw.rectangle([(radius, 0), (mx - radius, my)], fill=solid_fill)
    draw.rectangle([(0, radius), (mx, my - radius)], fill=solid_fill)

    return mask


if __name__ == '__main__':
    # url = ''
    # file = BytesIO(urlopen(url).read())

    img = Image.open('assets/images/image.png')
    x, y = 300, 1600
    radius = 30

    cropped_img = img.crop((x, y, 1000, 2600))

    blurred_img = cropped_img.filter(ImageFilter.GaussianBlur(20)).convert('RGBA')

    img.paste(blurred_img, (x, y), create_rounded_rectangle_mask(cropped_img, radius))

    img.save('assets/images/new.png')
    img.show()

    #    CENTER PICTURE
    # if img.size[0] > img.size[1]:
    #     size = img.size[1]
    #     llx, lly = (img.size[0] - img.size[1]) // 2, 0
    # else:
    #     size = img.size[0]
    #     llx, lly = 0, (img.size[1] - img.size[0]) // 2
    # urx, ury = llx + size + 1, lly + size + 1

    # Blur Image -> image.filter(ImageFilter.GaussianBlur(15)).save('image.png')

    # Add Font ->   draw = ImageDraw.Draw(image)
    #               font = ImageFont.truetype('BurbankBigCondensed-Bold.otf', 500)
    #               draw.text((500, 500), "Test", (75, 101, 132), font=font)

    # image.save('image.png')

    # Create Box (with transperency ->
    # img = Image.open('assets/images/image.png').convert('RGBA')
    #
    #     tmp = Image.new('RGBA', img.size, (0, 0, 0, 0))
    #
    #     draw = ImageDraw.Draw(tmp)
    #
    #     draw.rectangle(((100, 100), (1000, 1000)), fill=(255, 255, 255, 100))
    #
    #     img = Image.alpha_composite(img, tmp)
    #     img = img.convert('RGB')
    #     img.save('assets/images/image.png')

if __name__ == 'n':
    res = requests.get('https://fnbr.co/shop')
    res.raise_for_status()
    soup = bs4.BeautifulSoup(res.text, 'html.parser')
    soup = soup.html.body.div

    print(soup.prettify())

if __name__ == 'n':
    map = Image.open('assets/images/map.jpg')
    marker = Image.open('assets/images/marker.png')
    map.paste(marker, (865, 590), marker)
    map.save('assets/images/map_new.png', format="JPEG")
    map.show()

    # for div in soup2.find_all('div'):
    #     classes = div['class']
    #     print(classes)
