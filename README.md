<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/monitor-dark.svg">
  <img src="assets/monitor-light.svg" alt="A rotating 3D ASCII computer whose screen types: whoami, roha fatima, full stack dev, currently building learnmips.com" width="620">
</picture>

### Hi, I'm Roha Fatima

Full-stack developer · Computer Science @ UT Dallas

I build web apps end to end, from React front ends to Python and Java back ends.

<a href="https://www.learnmips.com">learnmips.com</a> ·
<a href="https://github.com/Roro141/CS_Portfolio">portfolio</a> ·
<a href="https://github.com/Roro141?tab=repositories">all repos</a>

<br><br>

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Java](https://img.shields.io/badge/Java-ED8B00?style=flat-square&logo=openjdk&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
![React](https://img.shields.io/badge/React-20232A?style=flat-square&logo=react&logoColor=61DAFB)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat-square&logo=css3&logoColor=white)

</div>

<br>

<details open>
<summary><code>$ ls projects/</code></summary>
<br>

| project | what it is | built with |
|---|---|---|
| [**learnmips.com**](https://www.learnmips.com) | Gamified platform for learning MIPS assembly: an in-browser editor with live register and memory views, guided tutorials, puzzles, and binary/hex math practice | Next.js · React |
| [**Portfolio**](https://github.com/Roro141/CS_Portfolio) | My personal portfolio site | JavaScript · HTML · CSS |

</details>

<details>
<summary><code>$ cat how_the_monitor_works.txt</code></summary>
<br>

The computer at the top is drawn by a small 3D software renderer I wrote in Python ([`scripts/render.py`](scripts/render.py)). It samples box geometry into surface points, rotates and perspective-projects them onto a character grid, depth-buffers, backface-culls, and shades each point with an ASCII luminance ramp. The screen text is mapped onto the monitor face cell by cell. The 108 frames are packed into one SVG and animated with CSS, since GitHub doesn't run JavaScript.

A GitHub Action re-renders it every day, pulling my most recently pushed repo into the "currently building" line.

</details>
