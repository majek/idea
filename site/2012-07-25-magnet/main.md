<%inherit file="base.html"/>


<article>
<%block filter="filters.markdown">

${title}
====================================

<div class="date">${date.strftime('%d %B %Y')}</div>

Some time ago I've read about a guy that had
[a magnet implanted in the pinky finger](http://www.iamdann.com/2012/03/21/my-magnet-implant-body-modification).

<div class="image" style="height:392px;"><img src="finger-magnet-implant.jpg" height="347px">
<div>(<a href="http://www.iamdann.com/2012/03/21/my-magnet-implant-body-modification">source</a>)</div></div>

The author sems to have made the implant mostly for fun only later he
discovered that it sometimes "ticks" in and gives basically a "sixth
sense":

> When people discuss magnet implants giving a “sixth sense,” this is
> what they’re talking about. I was working retail at the time, and I
> believe the first thing I noticed was the vibrations from the fan
> inside the cash register.

Later he discoveres more interesting things about the environmtent:

> The best part of having the magnet implant was discovering invisible
> magnetic fields when I wasn’t actually looking. The first experience
> I had with this was walking through the intersection of Broadway and
> Bleecker in Manhattan. I passed through this intersection a few
> times before realizing that my finger would tingle at a certain
> spot. After paying a bit more attention, I realized that I was
> feeling something underground. At first, I assumed it was a subway
> car, but later came to the conclusion that it was most likely the
> subway power generator, or the giant fan that was cooling these
> generator.

Having a sixth sense sounds exciting, but implanting a piece of metal
in your body is quite aggresive. Even ignoring such details like
finding a surgeon willing to perform the operation and getting a
suitable magnet, the prospect of
[not being able to get an MRI scan](http://news.ycombinator.com/item?id=3734200)
is a serious downside.

Deciding that an implant may not be for me I started to wonder: why
not to try "emulate" the thing? Of course, any kind of "emulation" is
inferior to real sensation in your finger, but at least I will be able
to unintrusively figure out if the whole idea is worthwhile.

Tinkering mode: ON
------------------

Devices that are used to detect magnetic fields are called
[magnetometers](https://en.wikipedia.org/wiki/Magnetometer). They are
quite commonspread - detecting magnetic field direction is exactly
what compasses do. And most likely you have one in your phone.

<div class="image" style="height:336px;"><img src="iphone-compass.jpg" height="327px"></div>

Having previously played with Arduino I thought about building a very
simple device that could be somehow worn and would notify the user
about magnetic field variations.

From Dann's post I understand that he can only feel when the magnetic
field is fluctuatng, but having a computer I'm able to detect all
kinds of changes in the field.

So I decided to start simple - Arduino, with a magnetometer connected
to it and a simple buzzer. I decided to re-use my iPod armband and
wear the device on my right arm.

The device will count the absolute strength of the magnetic field and
if it is stronger than threshold inform me with the buzzer. I guess
that's called
[wearable computing](https://en.wikipedia.org/wiki/Wearable_computing)
nowadays :)

Hardware setup
--------------

I'm not an electrical engineer, even simple tasks like getting data
from the magnetometer might be problematic in an Arduino
world. Luckily I found a
[blog post describing an Arduino talking to a simple magnetometer](http://www.geocomputing.co.uk/getpage.php?type=page&page=ppcmagnetest). The
magnetometer unit in use is
[HMC6352](https://www.sparkfun.com/products/7915). For $35 it's
expensive - but at least it's very simple.

The chip is simple works with Arduino out of the box and accepts input
voltage in a scale perfect for Ardunion 2.7V - 5.2V. But unfortunately
was not good enough for my usage - having only two axis appeared to be
too fragile. The readings were flaky and I often missed interesting
readings due to the lack of the third axis.

<div class="image" style="height:224px;"><img src="hmc5883l.jpg" height="196px"></div>

My next choice was [HMC5883L](https://www.sparkfun.com/products/10530)
for $15. The decent alternative might be
[MAG3110](https://www.sparkfun.com/products/10619) for the same prize
but a bit more sensitive. I chose HMC due to a better documentation,
namely this blog post:

 * http://bildr.org/2012/02/hmc5883l_arduino/
 
Now, the big problem with those chips is voltage - both operate in
around 2V - 3.6V range. 

Power supply
------------

<div class="image" style="height:224px;"><img src="lilypad.jpg" height="196px"></div>

Wearing a normal
[Arduino Uno Board](http://arduino.cc/en/Main/ArduinoBoardUno) is not
practical, fortunately there are many alternatives. I chose
[Arduino LilyPad Simple](https://www.sparkfun.com/products/10274). On
hindsight [Arduino Fio](https://www.sparkfun.com/products/10116) or
[Pro Mini](https://www.sparkfun.com/products/11114) might have been
better options.

[LilyPad](http://www.arduino.cc/en/Main/ArduinoBoardLilyPad) can be
powered with either from a Li-Po battery or from an USB (FTDI)
interface. The latter is mostly useful for development. Most
importantly - LilyPad does not provide a 3.3V power output like Uno
Board does.

Our precious magneometer HMC5883L will blow up when powered with
5V. In order to comprehend that I used a voltage regulator from
[LM1117](http://www.ti.com/lit/ds/symlink/lm1117-n.pdf) family. I got
3.3V one, as that was the only thing available in shop at a time.

With a regulator used to power magnetometer I could connect it to
LilyPad and power it either from Li-Po battery and from USB.

Oh, it's worth noting that the regulator is useful even when using
Li-Po battery as a power source - although the battery is rated as
3.7V,
[according to Wikipedia](https://en.wikipedia.org/wiki/Lithium-ion_polymer_battery)
you should expect voltage ranging from 2.7V when discharged to 4.23V
when charged.

Buzzer
------

<div class="image" style="height:224px;"><img src="buzzer.jpg" height="196px"></div>

Sorting out the buzzer was simple - SparkFun proivde
[ready-to-use buzzers](https://www.sparkfun.com/products/8463) crafted
for LilyPad.



</%block>
</article>
