import flutter
import serve
from rearrange import *
import resort
from datetime import datetime, date
import ntpath
import ui
from threading import Thread

line = "----------------------------------------------"
_workplace_path = "workplace.json"
_cache_folder = ".l10n_arb_tool"
_log_folder = "log"
logs = []
serve_thread: Thread | None = None
migration_version = 1
background_tasks = set()


def in_cache(sub: str) -> str:
    return ntpath.join(_cache_folder, sub)


def log_folder():
    return in_cache(_log_folder)


def log_path():
    d = date.today().isoformat()
    return ntpath.join(log_folder(), f"{d}.log")


class Workplace:
    def __init__(self):
        self.version = migration_version
        self.indent = 2
        self.prefix = "app_"
        self.l10n_folder = "lib/l10n"
        self.project_root = "."
        self.template_name = "app_en.arb"
        self.resort_method = resort.Alphabetical
        self.auto_add = True
        self.keep_unmatched_meta = False
        self.read_workplace = True
        self.auto_read_workplace = False
        self.auto_refresh = False


other_arb_paths = []

x = Workplace()
last_x = None


def workplace_path():
    return in_cache(_workplace_path)


def save_workplace(workplace: Workplace = x):
    path = workplace_path()
    j = json.dumps(vars(workplace), ensure_ascii=False, indent=2)
    write_fi(path, j)
    Log(f"workplace saved at {path}.")


# noinspection PyBroadException
def read_workplace() -> Workplace | None:
    path = workplace_path()
    raw = try_read_fi(path)
    workplace = None
    if raw is not None:
        Log(f"workplace was found at {path}")
        try:
            j = json.loads(raw)
        except:
            Log("workplace has been corrected.")
            delete_fi(path)
            Log("workplace was deleted.")
            return None
        workplace = Workplace()
        for k, v in j.items():
            if hasattr(workplace, k):
                setattr(workplace, k, v)
    return workplace


def D(*args):
    ui.terminal.print(*args)


def DLog(*args):
    ui.terminal.print_log(*args)


def Log(*args):
    ui.terminal.log(*args)


def C(prompt: str) -> str:
    return ui.terminal.input(prompt)


def yn(reply: str) -> bool:
    return to_bool(reply, empty_means=True)


def print_background_tasks():
    D(f"bg tasks: [{', '.join(background_tasks)}]")


class MigrationTerminal(ui.Terminal):
    def print(self, *args):
        print(f"|>", *args)

    def print_log(self, *args):
        content = ' '.join(args)
        print(f"|>", content)
        self.log(content)

    # noinspection PyBroadException
    def log(self, *args):
        content = ' '.join(args)
        now = datetime.now().strftime("%H:%M:%S")
        content = f"[{now}] {content}\n"
        if ensure_folder(log_folder()):
            try:
                append_fi(log_path(), content)
            except:
                pass
        logs.append(content)

    def input(self, prompt: str) -> str:
        return input(f"|>   {prompt}")


def template_path():
    return ntpath.join(x.l10n_folder, x.template_name)


def template_path_abs():
    return os.path.abspath(ntpath.join(x.l10n_folder, x.template_name))


def Dline(center: str = None):
    if center is None:
        print(line)
    else:
        print(f"|>-------------------{center}-------------------")


def cmd_add(args: list[str] = ()):
    D(f"enter a file name to be created. enter \"#\" to quit.")
    name = C("% ")
    if name == "#":
        return
    new = ntpath.join(x.l10n_folder, name)
    tplist, tpmap = load_arb(path=template_path())
    if x.auto_add:
        rearrange_others_saved_re([new], tplist, x.indent, x.keep_unmatched_meta, fill_blank=True)
        DLog(f"{new} was created and rearranged.")
    else:
        rearrange_others_saved_re([new], tplist, x.indent, x.keep_unmatched_meta, fill_blank=False)
        DLog(f"{new} was created.")


def cmd_rename(args: list[str] = ()):
    D(f"enter old name and then new name. enter \"#\" to quit.")
    while True:
        template_arb = load_arb_from(path=template_path())
        tplist, tpmap = template_arb.plist, template_arb.pmap
        old = C(f"old=")
        if old == "#":
            break
        if old not in tpmap.keys():
            # try to fuzzy match
            matched, ratio = fuzzy_match(old, tpmap.keys())
            if matched is not None:
                D(f"\"{old}\" isn't in template, do you mean \"{matched}\"?")
                confirmed = yn(C(f"y/n="))
                if not confirmed:
                    D("alright, let's start all over again.")
                    continue
                # if confirmed, do nothing
            else:
                D(f"\"{old}\" isn't in template, plz check typo.")
                continue
        while True:
            # for getting the
            new = C(f"new=")
            if new == "#":
                break
            if new == old:
                D("a new one can't be identical to the old one.")
            valid = validate_key(new)
            if not valid:
                D(f"the new key \"{new}\" is invalid, please enter again.")
            else:
                break
        other_arbs = load_all_arb_in(paths=other_arb_paths)
        arbs = other_arbs + [template_arb]
        for arb in arbs:
            if old in arb.pmap:
                arb.rename_key(old=old, new=new)
                Log(f"renamed \"{old}\" to \"{new}\" in \"{arb.file_name()}\".")
            else:
                if x.auto_add:
                    p = Pair(key=new, value="")
                    arb.add(p)
                    Log(f"added \"{new}\" in \"{arb.file_name()}\".")

        if x.resort_method is not None:  # auto_resort is enabled
            resorted = resort.methods[x.resort_method](template_arb.plist, template_arb.pmap)
            template_arb.plist = resorted
            if serve_thread is None:
                rearrange_others(other_arbs, template_arb, fill_blank=x.auto_add)
        for arb in arbs:
            save_flatten(arb, x.indent, x.keep_unmatched_meta)
            Log(f"{arb.file_name()} saved.")
        if x.auto_refresh:
            flutter.gen_110n(x.project_root)
        Dline("[renamed]")


# noinspection PyBroadException
def cmd_resort(args: list[str] = ()):
    size = len(resort.methods)
    if size == 0:
        D("No resort available.")
        return
    for index, name in resort.id2methods.items():
        D(f"{index}: {name}")  # index 2 name
    D("enter the number of method.")
    while True:
        try:
            inputted = C("method=")
            if inputted == "#":
                return
            i = int(inputted)
            if 0 <= i < size:
                break
            else:
                D(f"{i} is not in range(0<=..<{size})")
        except:
            D("input is invalid, plz try again.")
    template_arb = load_arb_from(path=template_path())
    method_name = resort.id2methods[i]
    template_arb.plist = resort.methods[method_name](template_arb.plist, template_arb.pmap)
    save_flatten(template_arb)
    rearrange_others_saved_re(other_arb_paths, template_arb.plist,
                              x.indent, x.keep_unmatched_meta,
                              fill_blank=x.auto_add)
    D("all .arb files were resorted and rearranged.")


def cmd_log():
    for ln in logs:
        D(ln)


def cmd_set(args: list[str] = ()):
    D("set the workplace")
    D(f"enter \"#\" to quit [set]. enter \"?\" to skip one.")
    settings = x
    fields = vars(settings)
    for k, v in fields.items():
        D(f"{k}={v}      << former")
        while True:
            inputted = C(f"{k}=")
            if inputted == "#":
                return
            if inputted == "?":
                break
            cast = try_cast(v, inputted)
            if cast is None:
                D(f"invalid input, \"{k}\"'s type is \"{type(v).__name__}\".")
            else:
                if hasattr(settings, k):
                    setattr(settings, k, v)
                break


serve_is_running = False


class NestedServerTerminal(ui.Terminal):
    def print(self, *args):
        Log(*args)

    def print_log(self, *args):
        Log(*args)

    def log(self, *args):
        Log(*args)


def cmd_serve(args: list[str] = ()):
    global serve_thread, serve_is_running
    D(f"[serve] will detect changes of \"{x.template_name}\" and rearrange others at background.")
    D(f"do you want to start the server?")
    reply = C("y/n=")
    if reply == "#":
        return
    start = yn(reply)
    if not start:
        return
    if serve_thread is None:
        server_is_running = True

        def serve_func():
            serve.start(template_path(), other_arb_paths,
                        x.indent, x.keep_unmatched_meta, fill_blank=True,
                        is_running=lambda: server_is_running,
                        on_rearranged=lambda: refresh() if x.auto_refresh else None,
                        terminal=NestedServerTerminal())

        serve_thread = Thread(target=serve_func)
        serve_thread.daemon = True
        serve_thread.start()
        background_tasks.add("serve")
        DLog(f"server started at background.")
    else:
        D("server has been started, do you want to stop it?")
        reply = C("y/n=")
        if reply == "#":
            return
        stop = yn(reply)
        if "serve" in background_tasks:
            background_tasks.remove("serve")
        if stop:
            server_is_running = False
            DLog(f"server aborted.")


def refresh(args: list[str] = ()):
    flutter.gen_110n(x.project_root)


def cmd_refresh(args: list[str] = ()):
    D(f"[refresh] will regenerate the .dart file by calling \"flutter gen-l10n\".")
    refresh()


cmds: dict[str, Callable[[], None]] = {
    "add": cmd_add,
    "rename": cmd_rename,
    "resort": cmd_resort,
    "log": cmd_log,
    "set": cmd_set,
    "serve": cmd_serve,
    "r": cmd_refresh
}
cmd_names = list(cmds.keys())
cmd_full_names = ', '.join(cmd_names)


def run_cmd(name: str, func: Callable[[], None]):
    Dline(f">>[{name}]<<")
    func()
    Dline(f"<<[{name}]>>")


def migrate():
    while True:
        D(f"enter \"quit\" or \"#\" to quit migration.")
        D(f"all cmds: [{cmd_full_names}]")
        if len(background_tasks) > 0:
            print_background_tasks()
        name = C("% ")
        if name == "quit" or name == "#":
            return
        if name in cmd_names:
            run_cmd(name, cmds[name])
        else:
            # try to fuzzy match
            matched, ratio = fuzzy_match(name, cmd_names)
            if matched is not None:
                D(f"cmd \"{name}\" is not found, do you mean \"{matched}\"?")
                confirmed = yn(C(f"y/n="))
                if not confirmed:
                    D("alright, let's start all over again.")
                else:
                    run_cmd(matched, cmds[matched])
            else:
                D(f"cmd \"{name}\" is not found, plz try again.")
        Dline()


def init():
    D("initializing .arb files...")
    for f in os.listdir(x.l10n_folder):
        full = ntpath.join(x.l10n_folder, f)
        if os.path.isfile(full):
            head, tail = ntpath.split(full)
            if tail != x.template_name and tail.endswith(".arb") and tail.startswith(x.prefix):
                other_arb_paths.append(full)
    Dline("[workplace]")
    D(f"{x.indent=},{x.prefix=},{x.l10n_folder=},{x.auto_add=}")
    D(f"{x.resort_method=}")
    Dline("[workplace]")
    D(f"l10n folder locates at {os.path.abspath(x.l10n_folder)}")
    D(f"all .arb file paths: [")
    for p in other_arb_paths:
        D(f"{os.path.abspath(p)}")
    D(f"]")
    D(f"template arb file path: \"{template_path_abs()}\"")
    D(f".arb files initialized.")


# noinspection PyBroadException
def setup_indent():
    D(f"please enter indent, \"{x.indent}\" as default")
    while True:
        inputted = C("indent=")
        try:
            if inputted == "#":
                return 1
            if inputted != "":
                x.indent = int(inputted)
            return
        except:
            D("input is invalid, plz try again.")


def setup_project_root():
    D(f"please enter the path of project root, \"{x.project_root}\" as default")
    while True:
        inputted = C("project_root=")
        if inputted == "#":
            return 1
        if inputted != "":
            x.project_root = inputted
        return


def setup_l10n_folder():
    D(f"please enter path of l10n folder, \"{x.l10n_folder}\" as default")
    while True:
        inputted = C("l10n_folder=")
        if inputted == "#":
            return 1
        if inputted != "":
            x.l10n_folder = inputted
        return


def setup_prefix():
    D(f"please enter prefix of .arb file name, \"{x.prefix}\" as default")
    while True:
        inputted = C("prefix=")
        if inputted == "#":
            return 1
        if inputted != "":
            x.prefix = inputted
        return


def setup_template_name():
    D(f"please enter template file name without extension, \"{x.template_name}\" as default")
    while True:
        inputted = C("folder=")
        if inputted == "#":
            return 1
        if inputted != "":
            x.template_name = inputted
        return


def setup_auto_add():
    D(f"\"auto_add\" will add missing key automatically , \"{x.auto_add}\" as default")
    while True:
        inputted = C("auto_add=")
        if inputted == "#":
            return 1
        if inputted != "":
            x.auto_add = to_bool(inputted)
        return


def setup_keep_unmatched_meta():
    D(f"\"keep_unmatched_meta\" will keep a meta even missing a pair, \"{x.keep_unmatched_meta}\" as default")
    while True:
        inputted = C("keep_unmatched_meta=")
        if inputted == "#":
            return 1
        if inputted != "":
            x.keep_unmatched_meta = to_bool(inputted)
        return


# noinspection PyBroadException
def setup_auto_resort():
    D(f"\"auto_resort\" will resort when any change by migration, \"{x.resort_method}\" as default")
    while True:
        for index, name in resort.id2methods.items():
            D(f"{index}: {name}")  # index 2 name
        D(f"-1: None -- disable auto_resort")  # index 2 name
        inputted = C("id=")
        if inputted == "#":
            return 1
        try:
            i = int(inputted)
            if 0 <= i < len(resort.id2methods):
                x.resort_method = resort.id2methods[i]
            else:
                x.resort_method = None
            return
        except:
            D("input is invalid, plz try again.")


# noinspection PyBroadException
def setup_auto_refresh():
    D(f"\"auto_refresh\" will re-generate .dart file when any change by migration, \"{x.auto_refresh}\" as default")
    while True:
        while True:
            inputted = C("auto_refresh=")
            if inputted == "#":
                return 1
            if inputted != "":
                x.auto_refresh = to_bool(inputted)
            return


all_setups: list[Callable[[], int | None]] = [
    setup_project_root,
    setup_l10n_folder,
    setup_indent,
    setup_prefix,
    setup_template_name,
    setup_auto_add,
    setup_keep_unmatched_meta,
    setup_auto_resort,
]


def wizard():
    global x
    D("hello, I'm the migration wizard.")
    D("enter \"#\" to go back to previous setup.")
    last = read_workplace()
    if last is not None and last.version == migration_version:
        if last.auto_read_workplace:
            x = last
            D(f"I restored the workplace you last used at \"{workplace_path()}\".")
        elif last.read_workplace:
            D(f"I found the workplace you last used at \"{workplace_path()}\"")
            D(f"do you want to continue this work?")
            continue_work = True
            inputted = C("y/n=")
            if inputted == "#":
                return 1
            if inputted != "":
                continue_work = yn(inputted)
            if continue_work:
                x = last
                D(f"oh nice, your workplace is restored.")
                D(f"do you want to auto restore workplace next time?")
                inputted = C("y/n=")
                auto_restore = True
                if inputted == "#":
                    return 1
                if inputted != "":
                    auto_restore = yn(inputted)
                last.auto_read_workplace = auto_restore
        return
    index = 0
    while index < len(all_setups):
        cur = all_setups[index]
        res = cur()
        if res == 1:
            index -= 2
        index += 1
        if index < 0:
            return 1
    return None


def load_workplace_from(args: list[str] = ()):
    paras = split_para(args)
    settings = x
    fields = vars(settings)
    for k, v in fields.items():
        while True:
            given = From(paras, Get=k, Or=None)
            if given is not None:
                cast = try_cast(v, given)
                if cast is None:
                    D(f"invalid input, \"{k}\"'s type is \"{type(v).__name__}\".")
                else:
                    if hasattr(settings, k):
                        setattr(settings, k, v)
                    break


def main(args: list[str] = ()):
    ui.terminal = MigrationTerminal()
    Dline()
    D(f"welcome to migration v{migration_version} !")
    D("if no input, the default value will be used.")
    D("for y/n question, the enter key means \"yes\".")
    wizard_res = None
    if len(args) == 0:
        wizard_res = wizard()
    else:
        load_workplace_from(args)
    Dline()
    if wizard_res is None:
        init()
        Dline()
        migrate()
    save_workplace(x)
    DLog("workplace saved")
    D(f"migration exited.")


if __name__ == '__main__':
    main()
