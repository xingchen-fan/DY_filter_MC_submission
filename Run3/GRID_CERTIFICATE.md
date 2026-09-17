# Getting a grid certificate

Nothing in `TUTORIAL.md` works without one. `submit_run3.sh` stops at the proxy
check, and if you get past that with a certificate the VO does not know, the
jobs fail hours later on the worker node instead.

Budget an hour, most of it waiting for CERN to issue the certificate. You do
this once a year: the certificate expires, and so does everything built on it.

---

## 1. Request the certificate

<https://ca.cern.ch/ca/> -> **New Grid User certificate**.

You will be asked to set an **import password**. Write it down. You need it
twice more below, and there is no way to recover it -- if you lose it, the only
fix is to request a new certificate.

The download is a `.p12` file, usually `myCertificate.p12`.

---

## 2. Install it in your browser

You need this to sign the AUP in step 3, and to read CERN pages that ask for a
certificate.

* **macOS**: double-click the `.p12` and it goes into Keychain Access. Chrome
  and Safari read from the keychain, so they pick it up with no further work.
* **Linux / Windows**: import it in the browser itself -- Chrome's
  *Settings -> Privacy and security -> Security -> Manage certificates*, Firefox's
  *Settings -> Privacy & Security -> View Certificates -> Your Certificates -> Import*.

Either way it asks for the import password from step 1.

**Check:** open <https://ca.cern.ch/ca/> again. The browser should offer your
new certificate when asked which one to use. If it offers nothing, the import
did not take, and step 3 will not work.

---

## 3. Sign the CMS AUP

A certificate that exists is not yet a certificate CMS accepts. Go to
[SWGuideLcgAccess](https://twiki.cern.ch/twiki/bin/view/CMSPublic/SWGuideLcgAccess)
and follow the `cms-auth` link. The browser asks which certificate to present --
your new one is now in the list -- and then shows the VO membership page.

Click **Re-sign AUP**.

Until this is done, `voms-proxy-init --voms cms` fails with a membership error
that does not mention the AUP at all.

---

## 4. Put it on lxplus

Rename the download rather than exporting it again -- re-exporting from the
browser produces a file the `openssl` commands below will not read.

```bash
mv ~/Downloads/myCertificate.p12 ~/mycert.p12
rsync -az ~/mycert.p12 <you>@lxplus.cern.ch:
```

Then on lxplus:

```bash
mkdir -p ~/.globus
mv ~/mycert.p12 ~/.globus/
cd ~/.globus
```

---

## 5. Convert it to the two files the grid tools read

```bash
rm -f usercert.pem userkey.pem
openssl pkcs12 -in mycert.p12 -clcerts -nokeys -out usercert.pem
openssl pkcs12 -in mycert.p12 -legacy -nocerts -out userkey.pem
chmod 400 usercert.pem userkey.pem
```

Three things about those commands:

**`-legacy` is not optional on lxplus.** CERN's `.p12` is encrypted with
algorithms OpenSSL 3 disabled by default, and without the flag the command
fails with a message about an unsupported algorithm that reads like the file is
corrupt. It is not.

**You are asked for two different passwords.** First the import password from
step 1, to open the `.p12`. Then, for the key, a new **PEM passphrase** of your
choosing. That second one is what `voms-proxy-init` will ask you for from then
on; it can be the same as the first, but it is a separate thing.

**`chmod 400` matters.** The grid tools refuse a key that anybody else can read,
and the error they give points at the key rather than at its permissions.

---

## 6. Check that it actually works

This is the only step that proves the previous five:

```bash
source /cvmfs/cms.cern.ch/common/crab-setup.sh
voms-proxy-init --rfc --voms cms -valid 192:00
voms-proxy-info -all | grep -E "subject|timeleft|VO|attribute"
```

It must print `VO: cms` and an `attribute` line. A proxy with no VO attributes
is a proxy CRAB will not submit with.

Check when your certificate runs out, and put it in your calendar:

```bash
openssl x509 -in ~/.globus/usercert.pem -noout -subject -enddate
```

---

## When it goes wrong

| what you see | what it means |
|---|---|
| `unsupported algorithm` from `openssl` | the `-legacy` flag is missing from the key command |
| `Cannot find file or dir: /home/<you>/.globus/usercert.pem` | the files are not in `~/.globus`, or are still named `myCertificate.p12` |
| `Couldn't find valid credentials` | wrong PEM passphrase, or the key is not `chmod 400` |
| `User unknown to this VO` | step 3 was skipped, or the AUP lapsed and needs re-signing |
| proxy exists but CRAB refuses | `voms-proxy-info -all` shows no `attribute` line: the proxy was made without `--voms cms` |
| everything worked last year, nothing works now | the certificate expired. Start again at step 1 |
