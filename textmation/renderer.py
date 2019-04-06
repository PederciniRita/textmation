#!/usr/bin/env python
# -*- coding: utf-8 -*-

from contextlib import contextmanager, redirect_stdout
from io import StringIO
import sys

from .properties import Point
from .elements import Element, Scene
from .rasterizer import Image, Font


def calc_frame_count(duration, frame_rate, *, inclusive=False):
	frames = duration * frame_rate
	if inclusive:
		frames += 1
	return frames


def iter_frame_time(duration, frame_rate, *, inclusive=False):
	for frame in range(calc_frame_count(duration, frame_rate, inclusive=inclusive)):
		time = frame / frame_rate
		yield frame, time


class Renderer:
	def __init__(self):
		self._image = None
		self._translations = [Point(0, 0)]

	@property
	def translation(self):
		return self._translations[-1]

	@contextmanager
	def translate(self, offset):
		self._translations.append(self.translation + offset)
		yield self
		self._translations.pop()

	def render(self, element):
		assert isinstance(element, Scene)
		image = self._render(element)
		assert isinstance(image, Image)
		return image

	def _render(self, element):
		assert isinstance(element, Element)
		method = "_render_%s" % element.__class__.__name__
		visitor = getattr(self, method)
		return visitor(element)

	def _render_children(self, element):
		for child in element.children:
			self._render(child)

	def _render_Scene(self, scene):
		self._image = Image.new(scene.size, scene.background)
		self._render_children(scene)
		return self._image

	def _render_Group(self, group):
		with self.translate(group.position):
			self._render_children(group)

	def _render_Rectangle(self, rect):
		self._image.draw_rect(self.translation + rect.bounds, rect.color, rect.outline_color, rect.outline_width)
		self._render_children(rect)

	def _render_Circle(self, circle):
		self._image.draw_circle(self.translation + circle.center, circle.radius, circle.color, circle.outline_color, circle.outline_width)
		self._render_children(circle)

	def _render_Ellipse(self, ellipse):
		self._image.draw_ellipse(self.translation + ellipse.center, ellipse.radius_x, ellipse.radius_y, ellipse.color, ellipse.outline_color, ellipse.outline_width)
		self._render_children(ellipse)

	def _render_Line(self, line):
		self._image.draw_line(self.translation + line.start_point, self.translation + line.end_point, line.color, line.width)
		self._render_children(line)

	def _render_Text(self, text):
		font = Font.load(text.font, text.font_size)
		self._image.draw_text(text.text, self.translation + text.position, text.color, font, text.anchor, text.alignment)
		self._render_children(text)


def _render(renderer, scene, time):
	scene.compute(time)
	return renderer.render(scene)


def render(scene, time=0):
	scene.reset()
	return _render(Renderer(), scene, time)


def render_animation(scene, *, inclusive=True):
	scene.reset()

	renderer = Renderer()

	frame_count = calc_frame_count(scene.duration, scene.frame_rate, inclusive=inclusive)

	add_newline = False

	frames = []
	for frame, time in iter_frame_time(scene.duration, scene.frame_rate, inclusive=inclusive):
		# print(f"\rRendering Frame {frame+1:04d}/{frame_count:04d} ({(frame+1)/frame_count*100:.0f}%)")

		sys.stdout.write(f"\rRendering Frame {frame+1:04d}/{frame_count:04d} ({(frame+1)/frame_count*100:.0f}%)")
		sys.stdout.flush()

		f = StringIO()
		try:
			with redirect_stdout(f):
				frames.append(_render(renderer, scene, time))
		finally:
			output = f.getvalue()
			if output:
				sys.stdout.write("\n")
				sys.stdout.write(output)
				sys.stdout.flush()
			elif frame == (frame_count - 1):
				add_newline = True

	if add_newline:
		sys.stdout.write("\n")

	return frames
