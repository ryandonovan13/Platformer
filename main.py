import random
import pygame
from pygame.locals import *



pygame.init()

pygame.init()
pygame.mixer.init()

pygame.mixer.music.load("flappybirdmusic.mp3")
pygame.mixer.music.play(-1)
clock = pygame.time.Clock()
fps = 60

screen_width = 288
screen_height = 610

# define game variables
ground_scroll = 0
scroll_speed = 2    # speed of the pipes AND the ground (was 4, lower = slower)
gravity = 0.3
bounce = 0.4       # how much speed is kept after a bounce (1 = perfectly bouncy)
max_pull = 100      # max drag distance in pixels
power = 0.2      # launch speed = pull distance * power
ground_top = 500    # y where the ground starts
game_over = False

pipe_gap = 150          # space between top and bottom pipe
pipe_frequency = 2500   # milliseconds between new pipes (higher because pipes are slower)
pipe_margin = 60        # min distance from the gap to the top of the screen / ground
last_pipe = pygame.time.get_ticks() - pipe_frequency   # makes the first pipe appear right away

screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Flappy Bird")

font_big = pygame.font.Font(None, 56)
font_small = pygame.font.Font(None, 30)

# load images
bg = pygame.image.load("background-day.png")
ground_img = pygame.image.load('base.png')


def draw_text(text, font, center):
    shadow = font.render(text, True, (0, 0, 0))
    img = font.render(text, True, (255, 255, 255))
    screen.blit(shadow, shadow.get_rect(center=(center[0] + 2, center[1] + 2)))
    screen.blit(img, img.get_rect(center=center))


class Bird(pygame.sprite.Sprite):
    def __init__(self, x, y):
        pygame.sprite.Sprite.__init__(self)
        self.images = []
        self.index = 0
        self.counter = 0
        for num in range(1, 4):
            img = pygame.image.load(f'yellowbird-{num}.png')
            self.images.append(img)
        self.image = self.images[self.index]
        self.rect = self.image.get_rect()
        self.rect.center = [x, y]

        # physics / aiming
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(0, 0)
        self.launched = False
        self.standing = False   # True when resting on the ground or on top of a pipe
        self.aiming = False
        self.pull = pygame.Vector2(0, 0)

    def aim(self, mouse_pos):
        # pull points the way the bird will fly (opposite of the drag)
        self.pull = self.pos - pygame.Vector2(mouse_pos)
        if self.pull.length() > max_pull:
            self.pull.scale_to_length(max_pull)

    def launch(self):
        if self.pull.length() > 10:      # ignore tiny drags
            self.vel = self.pull * power
            self.launched = True
        self.aiming = False
        self.pull = pygame.Vector2(0, 0)

    def resolve_pipes(self):
        # pipes are solid: the bird gets pushed out of them the shortest way
        w, h = self.rect.width, self.rect.height
        for pipe in pipe_group:
            bird_rect = pygame.Rect(0, 0, w, h)
            bird_rect.center = (round(self.pos.x), round(self.pos.y))
            if not bird_rect.colliderect(pipe.rect):
                continue
            pr = pipe.rect
            push_left = bird_rect.right - pr.left      # distance to move the bird left to get out
            push_right = pr.right - bird_rect.left
            push_up = bird_rect.bottom - pr.top
            push_down = pr.bottom - bird_rect.top
            smallest = min(push_left, push_right, push_up, push_down)

            if smallest == push_left:           # hit the pipe's left side
                self.pos.x -= push_left
                if self.vel.x > 0:
                    self.vel.x *= -bounce
            elif smallest == push_right:        # hit the pipe's right side
                self.pos.x += push_right
                if self.vel.x < 0:
                    self.vel.x *= -bounce
            elif smallest == push_up:           # landed on top of a pipe
                self.pos.y -= push_up
                if self.vel.y > 0:
                    self.vel.y *= -bounce
                if abs(self.vel.y) < 1:
                    self.vel.y = 0
                self.standing = True
            else:                               # hit the underside of a pipe
                self.pos.y += push_down
                if self.vel.y < 0:
                    self.vel.y *= -bounce

    def update(self):
        # animation
        self.counter += 1
        flap_cooldown = 5
        if self.counter > flap_cooldown:
            self.counter = 0
            self.index += 1
            if self.index >= len(self.images):
                self.index = 0
            self.image = self.images[self.index]

        # aiming
        if self.aiming:
            self.aim(pygame.mouse.get_pos())

        self.standing = False

        # flight
        if self.launched:
            self.vel.y += gravity
            self.pos += self.vel

        # pipes push the bird around
        self.resolve_pipes()

        hw = self.rect.width / 2
        hh = self.rect.height / 2

        # walls, ceiling and ground
        if self.pos.x - hw < 0:
            self.pos.x = hw
            self.vel.x *= -bounce
        elif self.pos.x + hw > screen_width:
            self.pos.x = screen_width - hw
            self.vel.x *= -bounce

        if self.pos.y - hh < 0:
            self.pos.y = hh
            self.vel.y *= -bounce

        if self.pos.y + hh > ground_top:
            self.pos.y = ground_top - hh
            self.vel.y *= -bounce
            self.vel.x *= 0.9
            if self.vel.length() < 1.5:
                self.vel = pygame.Vector2(0, 0)
                self.launched = False

        if not self.launched:
            self.standing = True

        self.rect.center = (round(self.pos.x), round(self.pos.y))

    def draw_arrow(self, surface):
        if not self.aiming or self.pull.length() < 10:
            return
        length = self.pull.length()
        direction = self.pull.normalize()
        perp = pygame.Vector2(-direction.y, direction.x)
        ratio = length / max_pull
        color = (255, int(255 * (1 - ratio)), 0)

        tip = self.pos + direction * (length * 1.2)
        base = tip - direction * 14

        pygame.draw.line(surface, (80, 80, 80), self.pos, self.pos - self.pull, 2)   # pull-back band
        pygame.draw.line(surface, color, self.pos, base, 5)
        pygame.draw.polygon(surface, color, [tip, base + perp * 9, base - perp * 9])


class Pipe(pygame.sprite.Sprite):
    def __init__(self, x, y, position):
        # y = center of the gap
        # position 1 = top pipe, -1 = bottom pipe
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.image.load('pipe-green.png')
        self.rect = self.image.get_rect()
        if position == 1:
            self.image = pygame.transform.flip(self.image, False, True)
            self.rect.bottomleft = [x, y - int(pipe_gap / 2)]
        elif position == -1:
            self.rect.topleft = [x, y + int(pipe_gap / 2)]

    def update(self):
        # move left, and delete the pipe once it is off the screen
        self.rect.x -= scroll_speed
        if self.rect.right < 0:
            self.kill()


bird_group = pygame.sprite.Group()
pipe_group = pygame.sprite.Group()

flappy = Bird(100, int(screen_height / 2))
bird_group.add(flappy)


run = True
while run:

    clock.tick(fps)

    # draw background
    screen.blit(bg, (0, 0))

    # generate a new pair of pipes with a random gap height
    time_now = pygame.time.get_ticks()
    if not game_over and time_now - last_pipe > pipe_frequency:
        gap_center = random.randint(pipe_margin + pipe_gap // 2,
                                    ground_top - pipe_margin - pipe_gap // 2)
        pipe_group.add(Pipe(screen_width, gap_center, -1))   # bottom pipe
        pipe_group.add(Pipe(screen_width, gap_center, 1))    # top pipe
        last_pipe = time_now

    pipe_group.draw(screen)
    if not game_over:
        pipe_group.update()

    bird_group.draw(screen)
    flappy.draw_arrow(screen)
    bird_group.update()

    # lose condition: a pipe pushes the bird against the left wall and crushes it
    if not game_over and flappy.rect.left <= 0:
        if any(flappy.rect.colliderect(p.rect) for p in pipe_group):
            game_over = True
            flappy.aiming = False
            flappy.pull = pygame.Vector2(0, 0)
            flappy.vel = pygame.Vector2(0, 0)   # bird drops straight down
            flappy.launched = True

    # draw and scroll the ground
    screen.blit(ground_img, (ground_scroll, ground_top))
    if not game_over:
        ground_scroll -= scroll_speed
        if abs(ground_scroll) > 60:
            ground_scroll = 0

    if game_over:
        draw_text("Game Over", font_big, (screen_width // 2, 200))
        draw_text("Click to restart", font_small, (screen_width // 2, 250))

    for event in pygame.event.get():
        if event.type == QUIT:
            run = False
        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            if game_over:
                # restart
                pipe_group.empty()
                bird_group.empty()
                flappy = Bird(100, int(screen_height / 2))
                bird_group.add(flappy)
                last_pipe = pygame.time.get_ticks()   # short pause before the first pipe
                game_over = False
            # grab the bird (when it's resting on the ground or on a pipe)
            elif (not flappy.launched or flappy.standing) and flappy.pos.distance_to(event.pos) < 40:
                flappy.aiming = True
        if event.type == MOUSEBUTTONUP and event.button == 1:
            if flappy.aiming:
                flappy.launch()

    pygame.display.update()
pygame.quit()