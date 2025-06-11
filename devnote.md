## Project Overview
The system is for learnchineseperth, a chinese school in Perth. in the system, we will include applications for students mainly, like typing, reading comprehension, listening, and speaking. so the UI should be professional, clean, and easy to use.

## Tasks
- [x] change dns afterclass.learnchineseperth.com.au to 170.64.162.255
- [x] a .sh file to restart django project with gunicorn. be sure collect statics, make migrations, migrate, restart gunicorn. understand the codebase then come up the script.
- [] pinyinit, add print button to print the pinyin file;
- [x] add user profile / description which could be used as the reference for AI to generate more suitable content. 


## namegen 
namegen, new a django application for Chinese name generation, the UI should be simple and easy to use.
the function should not require login, as this is for traffic attraction / leads generation. 

the function flow should be:
1. a form to collection user information, including:
    - first name (required) and surname (optional)
    - gender (required, including male, female, rather not to specify)
    - DOB (optional, indicate this is for considerations like Chinese zodiac calculation, season, etc.)
    - Personality traits (required, Dropdown (Brave, Kind, Artistic, Calm, Cheerful, Wise, etc.))
    - Preferred Style (tone of the name) 
        - Let users select the vibe of their name:
        - 🐉 Traditional/Classical (e.g. 明德、文君)
        - 🎨 Artistic/Poetic (e.g. 子墨、清风)
        - 🌟 Modern/Cool (e.g. 凯文、天宇)
        - 💼 Professional/Formal (e.g. 嘉明、思远)
2. use AI to generate the name, and display the name in the UI. with stylish free chinese font, big and bold, with pinyin, english meaning, audio pronunciation.

style to use @main.css to align the brand style.



## UI 
theme colour:
primary: #FE4D01
secondary: #FFD966
background: #ffffff

text colour:
primary: #151515
secondary: #333333






