from paradox.lib.crypto import _keygen, decrypt, encrypt

dec_text = b"Very hard text to be encrypted"
enc_text = b'\xe2\x14S\x8eW`v\xaaa\xc5=\xfe\x90\x94\xf2\x97\xf0\x1f\x19I\xf1\xa7"h\xe5*\xe8\x01\xd4\xdczk'
password = b"test123456"
generated_key = list(
    bytearray(
        b"t15\xeee26\xees3\xee\xeet4\xee\xee\xee\xee\xee\xee\xee\xee\xee\xee"
        b"\xee\xee\xee\xee\xee\xee\xee\xee]lY\xb7M\x7fI\xa7[h\x86h\\h\x86h"
        b"G\xa9G\xa9\xb2\\\xb2\\\xabE\xabE\xabE\xabE\x15y \x97#\\\x15\xb2"
        b"5]\xdb\xb3\x8f\xe7a\t\xcff!\x88\x85\xd9k7\xc6\x83(m\xaa\xefD\x01"
        b"\x8b\xf2\xd2E\x1fCV\xe4I\x14\xcf|K\xac\xcd\xc4\xa1\xc7\xe6n\xec5^i"
        b"\xd6U}\x10\xb6Y\x1d\x1cz\x88Z\x1f\xd5\x96\xc0$\xd5\xc1\x0er"
        b"\xd4x\xb5qa\xa6@.\xda\xef\xb1\xd8\x96\xc3\xbe\xae\x15LQM"
        b"\x0b\x83\xd9\xc61\xa7gC6\xf7\xf9\x8b\xe5\x9d(Y\xd5s3\x1d\xc0/\x9eF"
        b"\xabh\xd6x\xde\x92\xc3\x8eq\xf2+\xed\x8d*M\x0e/\xd8!\xaa"
        b"A\xdc\xf4\xad\x80\xf3\xc0\xddkD\xda\x9c\x07o\xb9\xc1K\xd9\x1a\x94"
        b"\xef\x1d6\xdb\xf5\xdf\x92\x9c\r\xd5\xf4^\x80\\\xa8\x05"
    )
)


def test_keygen():
    assert generated_key == _keygen(password)


def test_encrypt():
    assert enc_text == encrypt(dec_text, password)


def test_decrypt():
    assert dec_text == decrypt(enc_text, password).rstrip(b"\xee")
