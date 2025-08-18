import hil2.hil2 as hil2
import mk_assert.mk_assert as mka


def do_test(h: hil2.Hil2):
    do_2 = h.do("MainTester", "DO@2")
    di_28 = h.di("MainTester", "DI@28")

    do_2.set(True)
    val = di_28.get()
    mka.assert_true(val, "DI@28 should be True after setting DO@2 to True")


def main():
    with hil2.Hil2(
        "./tests/example/config.json",
        "device_configs",
        "netmap.csv",
        "can.dbc",
    ) as h:
        mka.add_test(do_test, h)

        mka.run_tests()

    # v_bat = h.ao("Main_Module", "VBatt")
    # v_bat.set(3.2)
    # val = v_bat.get()

    # h.set_ao("Main_Module", "VBatt", 3.2)
    # val = h.get_ao("Main_Module", "VBatt")

    # h.get_last_can("HIL2", "MCAN", "Signal")

    # mcan = h.can("HIL2", "MCAN")
    # mcan.send("Signal", {})
    # mcan.send(23, {})
    # sig_dict = mcan.get_last("Signal")
    # sig_dict = mcan.get_last(23)
    # sig_dicts = mcan.get_all("Signal")
    # sig_dicts = mcan.get_all(23)
    # sig_dicts = mcan.get_all()
    # mcan.clear("Signal")
    # mcan.clear(23)
    # mcan.clear()


if __name__ == "__main__":
    main()
