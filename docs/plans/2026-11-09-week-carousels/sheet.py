import sys, glob
from PIL import Image
S='/tmp/claude-0/-home-user-growth-makeyourmindup/b1314669-5b18-56a6-a214-e2b23dfe4ba3/scratchpad'
for d in sys.argv[1:]:
    fs=sorted(glob.glob(f'{d}/cards/card-*.png'),key=lambda f:int(f.split('-')[-1][:-4]))
    ims=[Image.open(f).resize((540,675)) for f in fs]
    cols=4; rows=(len(ims)+cols-1)//cols
    w=Image.new('RGB',(540*cols,675*rows))
    for i,im in enumerate(ims): w.paste(im,((i%cols)*540,(i//cols)*675))
    w.save(f'{S}/sheet-{d}.png')
