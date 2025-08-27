import hil2.hil2 as hil2
import mk_assert.mk_assert as mka

import logging


def do_test(h: hil2.Hil2):
    do_2 = h.do("HIL2Bread", "DO@2")
    di_28 = h.di("HIL2Bread", "DI@28")
    ai_14 = h.ai("HIL2Bread", "AI@14")

    do_2.set(True)
    val = di_28.get()
    a = ai_14.get()
    print(f"DI@28: {val}, AI@14: {a}")
    mka.assert_true(val, "DI@28 should be True after setting DO@2 to True")
    mka.assert_eqf(a, 3.3, 0.5, "AI@14 should be approximately 3.3V")

    do_2.set(False)
    val = di_28.get()
    a = ai_14.get()
    print(f"DI@28: {val}, AI@14: {a}")
    mka.assert_false(val, "DI@28 should be False after setting DO@2 to False")
    mka.assert_eqf(a, 0.0, 0.5, "AI@14 should be approximately 0.0V")


def main():
    logging.basicConfig(level=logging.DEBUG)
    
    with hil2.Hil2(
        "./tests/example/config.json",
        "device_configs",
        None,
        None
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
